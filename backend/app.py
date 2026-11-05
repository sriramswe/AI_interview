import base64
from copy import deepcopy
import json
import logging
import os
import math
from io import BytesIO
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).with_name(".env"))

from fastapi import Depends, FastAPI, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pypdf import PdfReader
import qrcode
import qrcode.image.svg
from sqlalchemy import delete as sql_delete, func, inspect, select, update
from sqlalchemy.orm import Session
from auth import auth_utils
from core import database, models, schemas
from core.behavioral_analysis import analyze_speaking_metrics
from core.round_config import (
    get_first_round,
    get_next_round,
    get_round_config,
    get_rounds_for_role,
    should_proceed_to_next_round,
)
from core.nlp_engine import evaluate_answer as evaluate_answer_nlp
from services.company_intelligence import get_company_intelligence
from services.development_workflow import development_workflow_agents
from services.billing import (
    PLAN_PRICES_RUPEES,
    PLAN_QUOTAS,
    PLAN_RANK,
    activate_subscription,
    build_upi_payment_uri,
    get_active_subscription,
    get_user_plan,
    normalize_plan,
)
from services.resume_builder import (
    FREE_RESUME_BUILD_LIMIT,
    MAX_RESUME_UPLOAD_SIZE_BYTES,
    RESUME_TEMPLATE_BY_ID,
    RESUME_TEMPLATES,
)
from services.resume_interview import (
    resolve_technical_categories,
    shuffled_category_plan,
)
from services.coding_round_service import (
    normalize_judgement,
    validate_hint,
    validate_problem,
    validate_roadmap,
)
from services.gemini_service import AIProviderTimeout, gemini_service
from services.intelligence_service import get_intelligence_service
from services.memory_service import get_memory_service
from services.visualizer import generate_performance_chart
from utils.resume_parser import (
    analyze_resume_interview_context,
    analyze_resume_match,
    calculate_detailed_ats_score,
    chunk_resume_context,
    parse_resume_skills_from_bytes,
)

logger = logging.getLogger(__name__)

MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024
MAX_PAYMENT_SCREENSHOT_SIZE_BYTES = 5 * 1024 * 1024


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.Base.metadata.create_all(bind=database.engine)
    _ensure_user_profile_columns()
    _sync_configured_admin_roles()
    yield


app = FastAPI(
    title="Interview Prep AI Platform",
    description="Interview backend using MySQL, NLP, subscriptions, and domain-aware rounds",
    version="2.2.0",
    lifespan=lifespan,
)

cors_origins = {
    origin.strip().rstrip("/")
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip().rstrip("/")
}
cors_origins.add("https://ai-interview-prep-swart-mu.vercel.app")

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _validate_hiring_report(value: dict) -> dict:
    verdicts = {"HIRE", "LEAN HIRE", "LEAN NO HIRE", "NO HIRE"}
    score = value.get("overall_score")
    if isinstance(score, bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hiring report returned an invalid score.",
        )
    try:
        numeric_score = float(score)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hiring report returned an invalid score.",
        ) from error
    if not math.isfinite(numeric_score) or not 0 <= numeric_score <= 10:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hiring report score must be between 0 and 10.",
        )
    if value.get("final_verdict") not in verdicts:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hiring report returned an invalid final verdict.",
        )
    for field in ("strengths", "areas_to_improve"):
        if not isinstance(value.get(field), list) or any(
            not isinstance(item, str) or not item.strip() for item in value[field]
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI hiring report returned invalid evidence lists.",
            )
    if not isinstance(value.get("recruiter_closing_note"), str) or not value["recruiter_closing_note"].strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hiring report is missing its closing note.",
        )
    value["overall_score"] = round(numeric_score, 1)
    return value


def _apply_feedback_tier(report: dict, plan: str) -> dict:
    if plan == "free":
        report.pop("strengths", None)
        report.pop("areas_to_improve", None)
    return report


@app.exception_handler(RuntimeError)
async def service_runtime_error_handler(_, error: RuntimeError):
    logger.error("Backend runtime exception: %s", error)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": str(error)},
    )


@app.exception_handler(AIProviderTimeout)
async def ai_provider_timeout_handler(_, error: AIProviderTimeout):
    logger.warning("AI provider timed out while processing a request: %s", error)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={
            "detail": "The AI provider timed out before this request could finish. Check the configured provider and model availability, then retry."
        },
        headers={"Retry-After": "5"},
    )


def _token_response(user: models.User) -> dict:
    return {
        "access_token": auth_utils.create_access_token({"sub": user.email}),
        "token_type": "bearer",
        "user": user.to_public_dict(),
    }


def _ensure_user_profile_columns(engine=None) -> None:
    target_engine = engine or database.engine
    with target_engine.begin() as connection:
        columns = {
            column["name"] for column in inspect(connection).get_columns("users")
        }
        if "gender" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN gender VARCHAR(32) NULL"
            )
        if "role" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE users ADD COLUMN role VARCHAR(20) "
                "NOT NULL DEFAULT 'user'"
            )


def _sync_configured_admin_roles() -> None:
    admin_emails = _configured_emails("SUPER_ADMIN_EMAILS")
    if not admin_emails:
        return
    with database.SessionLocal() as db:
        db.execute(
            update(models.User)
            .where(func.lower(models.User.email).in_(admin_emails))
            .values(role="admin")
        )
        db.commit()


def _decode_model_json(raw: str) -> dict:
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned[3:]
        if cleaned[:4].casefold() == "json":
            cleaned = cleaned[4:]
        cleaned = cleaned.removesuffix("```").strip()

    decoder = json.JSONDecoder()
    for index, character in enumerate(cleaned):
        if character != "{":
            continue
        try:
            result, _ = decoder.raw_decode(cleaned[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(result, dict):
            return result

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="The AI service returned an invalid response payload.",
    )


def _get_owned_interview_session(
    db: Session, session_id: int, current_user: models.User
) -> models.InterviewSession:
    interview_session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == session_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if not interview_session:
        raise HTTPException(status_code=404, detail="Interview not found.")
    return interview_session


def _candidate_profile_payload(
    profile: models.CandidateProfile | None,
) -> dict | None:
    if profile is None:
        return None
    return {
        "employment_status": profile.employment_status,
        "education_level": profile.education_level,
        "institution": profile.institution,
        "field_of_study": profile.field_of_study,
        "current_role": profile.current_role,
        "years_of_experience": profile.years_of_experience,
    }


def _candidate_profile_context(profile: models.CandidateProfile | None) -> str | None:
    data = _candidate_profile_payload(profile)
    if not data:
        return None
    labels = {
        "school_student": "school student",
        "college_student": "college student",
        "employed": "currently employed",
        "unemployed": "currently seeking work",
        "career_changer": "changing careers",
        "recent_graduate": "recent graduate",
        "other": "other",
    }
    return "; ".join(
        value
        for value in (
            f"Stage: {labels.get(data['employment_status'], data['employment_status'])}",
            f"Education: {data['education_level'] or ''} at {data['institution'] or ''}".strip(" at"),
            f"Field of study: {data['field_of_study']}" if data["field_of_study"] else "",
            f"Current role: {data['current_role']}" if data["current_role"] else "",
            (
                f"Years of experience: {data['years_of_experience']:g}"
                if data["years_of_experience"] is not None
                else ""
            ),
        )
        if value
    )


def _session_candidate_context(session: models.InterviewSession) -> str | None:
    profile = next(
        (
            item.get("candidate_profile")
            for item in session.transcript or []
            if item.get("role") == "system"
            and isinstance(item.get("candidate_profile"), dict)
        ),
        None,
    )
    if not profile:
        return None
    labels = {
        "school_student": "school student",
        "college_student": "college student",
        "employed": "currently employed",
        "unemployed": "currently seeking work",
        "career_changer": "changing careers",
        "recent_graduate": "recent graduate",
        "other": "other",
    }
    return "; ".join(
        value
        for value in (
            f"Stage: {labels.get(profile.get('employment_status'), profile.get('employment_status'))}",
            f"Education: {profile.get('education_level') or ''} at {profile.get('institution') or ''}".strip(" at"),
            f"Field of study: {profile['field_of_study']}" if profile.get("field_of_study") else "",
            f"Current role: {profile['current_role']}" if profile.get("current_role") else "",
            (
                f"Years of experience: {profile['years_of_experience']:g}"
                if isinstance(profile.get("years_of_experience"), (int, float))
                else ""
            ),
        )
        if value
    )


def _session_company_intelligence(session: models.InterviewSession):
    return next(
        (
            item.get("company_intelligence")
            for item in session.transcript or []
            if item.get("role") == "system"
            and item.get("company_intelligence") is not None
        ),
        None,
    )


def _session_category_plan(session: models.InterviewSession) -> list[str]:
    return next(
        (
            item.get("technical_category_plan")
            for item in session.transcript or []
            if item.get("role") == "system"
            and isinstance(item.get("technical_category_plan"), list)
        ),
        [],
    )


def _next_session_question_category(
    session: models.InterviewSession,
) -> str | None:
    if "technical" not in session.interview_round.casefold():
        return None
    plan = _session_category_plan(session)
    if not plan:
        return None
    asked_count = sum(
        1
        for item in session.transcript or []
        if isinstance(item, dict)
        and item.get("role") == "assistant"
        and item.get("round") == session.interview_round
    )
    return plan[asked_count % len(plan)]


async def _generate_session_question(
    db: Session,
    session: models.InterviewSession,
    company_intel,
    *,
    include_history: bool,
) -> tuple[str, str | None]:
    transcript = session.transcript if isinstance(session.transcript, list) else []
    chat_history = [
        item["content"]
        for item in transcript
        if isinstance(item, dict)
        and item.get("role") in {"assistant", "user"}
        and isinstance(item.get("content"), str)
    ] if include_history else []
    question_category = _next_session_question_category(session)
    company_for_question = session.target_company
    company_intel_for_question = company_intel
    usage_id = None
    if company_for_question:
        company_question_allowed, usage_id = _reserve_monthly_usage(
            db, session.user, "company_question", required=False
        )
        if not company_question_allowed:
            company_for_question = None
            company_intel_for_question = None
    try:
        question = await gemini_service.generate_interview_question(
            role=session.role_category,
            sub_role=session.sub_role,
            difficulty=session.difficulty_level,
            company=company_for_question,
            round_name=session.interview_round,
            jd=session.job_description,
            resume_text=(
                chunk_resume_context(session.resume_text)
                if session.resume_text
                else None
            ),
            chat_history=chat_history,
            current_time=datetime.now(timezone.utc).isoformat(),
            interviewer_name=session.interviewer_name,
            round_criteria=[
                *get_round_config(session.interview_round)["evaluation_criteria"],
                *(
                    [f"Focus this question on the {question_category} category."]
                    if question_category
                    else []
                ),
            ],
            candidate_context=_session_candidate_context(session),
            company_intel=company_intel_for_question,
            question_category=question_category,
        )
    except Exception:
        _release_monthly_usage(db, usage_id)
        raise
    return question, question_category


def _get_or_create_coding_ledger(
    db: Session, session_id: int, user_id: int
) -> models.CodingRoundLedger:
    ledger = db.scalar(
        select(models.CodingRoundLedger)
        .where(
            models.CodingRoundLedger.session_id == session_id,
            models.CodingRoundLedger.user_id == user_id,
        )
        .with_for_update()
    )
    if ledger:
        return ledger
    ledger = models.CodingRoundLedger(
        session_id=session_id,
        user_id=user_id,
        ledger_data={
            "current_round": 1,
            "unlocked_rounds": [1],
            "status": "active",
            "rounds": {
                "1": {
                    "status": "active",
                    "problem": None,
                    "hints": [],
                    "attempts": [],
                    "latest_evaluation": None,
                    "roadmap": None,
                    "roadmap_completed": False,
                }
            },
        },
    )
    db.add(ledger)
    db.flush()
    return ledger


async def _generate_coding_problem(
    interview_session: models.InterviewSession,
    round_number: int,
    language: str,
) -> dict:
    try:
        company_intel = await _get_company_intelligence(
            interview_session.target_company,
            interview_session.job_description,
            _session_target_geography(interview_session),
        )
        if company_intel is not None:
            if isinstance(company_intel, dict):
                company_context_data = {
                    key: company_intel[key]
                    for key in (
                        "name",
                        "industry",
                        "interview_style",
                        "cultural_values",
                    )
                    if key in company_intel
                }
                interview_rounds = company_intel.get("interview_rounds")
                if isinstance(interview_rounds, dict):
                    technical_round = next(
                        (
                            round_data
                            for round_name, round_data in interview_rounds.items()
                            if isinstance(round_name, str)
                            and any(
                                term in round_name.casefold()
                                for term in ("technical", "coding")
                            )
                            and isinstance(round_data, dict)
                        ),
                        None,
                    )
                    if technical_round:
                        company_context_data["technical_round"] = {
                            key: technical_round[key]
                            for key in ("focus", "common_topics", "style")
                            if key in technical_round
                        }
                company_context = json.dumps(
                    company_context_data, ensure_ascii=True, default=str
                )[:3000]
            else:
                company_context = str(company_intel)[:3000]
        else:
            company_context = None
        raw = await gemini_service.generate_coding_problem(
            role=interview_session.role_category,
            sub_role=interview_session.sub_role,
            difficulty=interview_session.difficulty_level,
            company=interview_session.target_company,
            company_intel=company_context,
            resume_text=interview_session.resume_text,
            round_number=round_number,
            language=language,
        )
    except AIProviderTimeout as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "Coding challenge generation timed out. Check that the configured "
                "AI provider is responsive, or increase AI_TIMEOUT_SECONDS if "
                "longer generation is expected."
            ),
        ) from error
    problem = validate_problem(_decode_model_json(raw))
    problem["language"] = language
    return problem


def _validate_vibe_assessment(value: object) -> dict:
    categories = ("confidence", "technical_depth", "assertiveness")
    if not isinstance(value, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation did not include a valid vibe assessment.",
        )
    normalized = {}
    for category in categories:
        item = value.get(category)
        if not isinstance(item, dict) or not isinstance(item.get("evidence"), str):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI evaluation returned an invalid vibe assessment.",
            )
        try:
            score = float(item["score"])
        except (KeyError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI evaluation returned an invalid vibe score.",
            ) from error
        if isinstance(item.get("score"), bool) or not math.isfinite(score) or not 0 <= score <= 10:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Vibe assessment scores must be between 0 and 10.",
            )
        evidence = item["evidence"].strip()
        if not evidence:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Vibe assessment evidence cannot be blank.",
            )
        normalized[category] = {
            "score": round(score, 1),
            "evidence": evidence,
        }
    return normalized


def _extract_resume_text(file_content: bytes) -> str:
    try:
        reader = PdfReader(BytesIO(file_content))
        resume_text = "\n".join(page.extract_text() or "" for page in reader.pages)
    except Exception as error:
        raise HTTPException(
            status_code=400, detail="Could not read the uploaded PDF."
        ) from error
    if not resume_text.strip():
        raise HTTPException(
            status_code=400, detail="The PDF contains no extractable text."
        )
    return resume_text


def _session_target_geography(session: models.InterviewSession) -> str | None:
    return next(
        (
            item.get("target_geography")
            for item in session.transcript or []
            if isinstance(item, dict)
            and item.get("role") == "assistant"
            and item.get("target_geography")
        ),
        None,
    )


async def _get_company_intelligence(
    company: str | None,
    job_description: str | None,
    geography: str | None = None,
):
    if not company:
        return None
    try:
        return await get_intelligence_service().get_intelligence(
            company, job_description, geography
        )
    except Exception:
        logger.exception("Could not retrieve company intelligence for %s", company)
        raise


def _require_plan(
    db: Session, current_user: models.User, minimum_plan: str
) -> str:
    current_plan = get_user_plan(db, current_user.id)
    if PLAN_RANK[current_plan] < PLAN_RANK[minimum_plan]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This feature requires the {minimum_plan.title()} plan.",
        )
    return current_plan


def _configured_emails(variable_name: str) -> set[str]:
    return {
        email.strip().casefold()
        for email in os.getenv(variable_name, "").split(",")
        if email.strip()
    }


def _is_super_admin(user: models.User) -> bool:
    return (
        user.role == "admin"
        and user.email.casefold() in _configured_emails("SUPER_ADMIN_EMAILS")
    )


def _require_admin(current_user: models.User) -> None:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access is required.",
        )


def _require_super_admin(current_user: models.User) -> None:
    if not _configured_emails("SUPER_ADMIN_EMAILS"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Super-admin access is not configured.",
        )
    if not _is_super_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super-admin access is required.",
        )


def _require_resume_subscription(
    db: Session, current_user: models.User
) -> str:
    current_plan = get_user_plan(db, current_user.id)
    if current_plan not in {"legacy_resume", "elite"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Resume upload and customization require an active Elite or legacy resume subscription.",
        )
    return current_plan


def _resume_document_payload(document: models.ResumeDocument) -> dict:
    return {
        "id": document.id,
        "template_id": document.template_id,
        "title": document.title,
        "source": document.source,
        "content": document.content,
        "created_at": document.created_at.isoformat(),
        "updated_at": document.updated_at.isoformat(),
    }


def _admin_user_payload(
    user: models.User,
    access_control: models.UserAccessControl | None,
    subscription: models.Subscription | None,
) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "gender": user.gender,
        "role": user.role,
        "created_at": user.created_at.isoformat(),
        "super_admin": _is_super_admin(user),
        "suspended": bool(access_control and access_control.suspended),
        "plan": normalize_plan(subscription.plan) if subscription else "free",
        "subscription_expires_at": (
            subscription.expires_at.isoformat() if subscription else None
        ),
    }


def _reserve_interview_quota(
    db: Session, current_user: models.User
) -> int | None:
    plan = get_user_plan(db, current_user.id)
    limit = PLAN_QUOTAS[plan]["interviews"]
    if limit is None:
        usage = models.PlanUsage(user_id=current_user.id, usage_type="interview")
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return usage.id
    db.execute(
        select(models.User.id)
        .where(models.User.id == current_user.id)
        .with_for_update()
    ).scalar_one()
    interval_start = _utc_month_start()
    saved_interviews = db.scalar(
        select(func.count())
        .select_from(models.InterviewSession)
        .where(
            models.InterviewSession.user_id == current_user.id,
            models.InterviewSession.created_at >= interval_start,
        )
    ) or 0
    reserved_interviews = _monthly_usage_count(db, current_user.id, "interview")
    if max(saved_interviews, reserved_interviews) >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"The {plan.title()} plan allows {limit} mock interviews per month.",
        )
    usage = models.PlanUsage(user_id=current_user.id, usage_type="interview")
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return usage.id


def _utc_month_start() -> datetime:
    return datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )


def _monthly_usage_count(db: Session, user_id: int, usage_type: str) -> int:
    return db.scalar(
        select(func.count())
        .select_from(models.PlanUsage)
        .where(
            models.PlanUsage.user_id == user_id,
            models.PlanUsage.usage_type == usage_type,
            models.PlanUsage.created_at >= _utc_month_start(),
        )
    ) or 0


def _reserve_monthly_usage(
    db: Session,
    current_user: models.User,
    usage_type: str,
    *,
    required: bool,
) -> tuple[bool, int | None]:
    plan = get_user_plan(db, current_user.id)
    quota_key = {
        "interview": "interviews",
        "resume_analysis": "resume_analyses",
        "company_question": "company_questions",
    }[usage_type]
    limit = PLAN_QUOTAS[plan][quota_key]
    if limit == 0:
        if required:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company-specific questions require an active Pro or Elite plan.",
            )
        return False, None
    if limit is None:
        usage = models.PlanUsage(user_id=current_user.id, usage_type=usage_type)
        db.add(usage)
        db.commit()
        db.refresh(usage)
        return True, usage.id

    db.execute(
        select(models.User.id)
        .where(models.User.id == current_user.id)
        .with_for_update()
    ).scalar_one()
    used = _monthly_usage_count(db, current_user.id, usage_type)
    if used >= limit:
        if required:
            feature_name = {
                "interview": "mock interviews",
                "resume_analysis": "resume analyses",
                "company_question": "company-specific questions",
            }[usage_type]
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"You have used all {limit} {feature_name} for this month.",
            )
        return False, None

    usage = models.PlanUsage(user_id=current_user.id, usage_type=usage_type)
    db.add(usage)
    db.commit()
    db.refresh(usage)
    return True, usage.id


def _release_monthly_usage(db: Session, usage_id: int | None) -> None:
    if usage_id is None:
        return
    db.execute(
        sql_delete(models.PlanUsage).where(models.PlanUsage.id == usage_id)
    )
    db.commit()


def _require_payment_reviewer(current_user: models.User) -> None:
    if current_user.role == "admin":
        return
    reviewer_emails = _configured_emails("PAYMENT_REVIEWER_EMAILS")
    super_admin_emails = _configured_emails("SUPER_ADMIN_EMAILS")
    if not reviewer_emails and not super_admin_emails:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment review is not configured.",
        )
    if (
        current_user.email.casefold() not in reviewer_emails
        and not _is_super_admin(current_user)
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Payment reviewer access is required.",
        )


# ==========================================
# MODULE 1: AUTHENTICATION
# ==========================================

@app.get("/health")
async def health():
    return {"status": "ok", "version": app.version}


@app.post("/api/chat/project")
async def chat_about_project(
    payload: schemas.ProjectChatRequest,
    _: models.User = Depends(auth_utils.get_current_user),
):
    history = [
        {"role": turn.role, "content": turn.content}
        for turn in payload.history
    ]
    try:
        answer = await gemini_service.chat_about_project(
            message=payload.message, history=history
        )
    except AIProviderTimeout:
        raise
    except RuntimeError as error:
        logger.exception("Project chatbot could not answer a request")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Project help is temporarily unavailable. Please try again later.",
        ) from error
    return {"answer": answer}


def _development_workflow_response(workflow: models.DevelopmentWorkflow) -> dict:
    return {
        "id": workflow.id,
        "task_description": workflow.task_description,
        "status": workflow.status,
        "plan": workflow.plan,
        "agent_outputs": workflow.agent_outputs,
        "test_attempts": workflow.test_attempts,
        "test_results": workflow.test_results,
        "deployment": workflow.deployment,
        "monitoring": workflow.monitoring,
        "created_at": workflow.created_at.isoformat(),
        "updated_at": workflow.updated_at.isoformat(),
    }


def _get_owned_development_workflow(
    workflow_id: int, user_id: int, db: Session
) -> models.DevelopmentWorkflow:
    workflow = db.scalar(
        select(models.DevelopmentWorkflow).where(
            models.DevelopmentWorkflow.id == workflow_id,
            models.DevelopmentWorkflow.user_id == user_id,
        )
    )
    if workflow is None:
        raise HTTPException(status_code=404, detail="Development workflow not found.")
    return workflow


@app.post("/api/development/workflows", status_code=status.HTTP_201_CREATED)
async def create_development_workflow(
    payload: schemas.DevelopmentWorkflowCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    workflow = models.DevelopmentWorkflow(
        user_id=current_user.id,
        task_description=payload.task_description,
        status="planning",
        agent_outputs={},
        test_attempts=0,
        test_results=[],
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    try:
        agent_state = await development_workflow_agents.create_proposals(
            workflow.task_description
        )
    except RuntimeError as error:
        workflow.status = "failed"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    workflow.plan = agent_state["plan"]
    workflow.agent_outputs = {
        "backend": agent_state["backend_proposal"],
        "database": agent_state["database_proposal"],
        "frontend": agent_state["frontend_proposal"],
        "integration": agent_state["integration_plan"],
    }
    workflow.status = "awaiting_tests"
    db.commit()
    db.refresh(workflow)
    return _development_workflow_response(workflow)


@app.get("/api/development/workflows")
def list_development_workflows(
    limit: int = 20,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    bounded_limit = max(1, min(limit, 100))
    workflows = db.scalars(
        select(models.DevelopmentWorkflow)
        .where(models.DevelopmentWorkflow.user_id == current_user.id)
        .order_by(models.DevelopmentWorkflow.created_at.desc())
        .limit(bounded_limit)
    ).all()
    return [_development_workflow_response(item) for item in workflows]


@app.get("/api/development/workflows/{workflow_id}")
def get_development_workflow(
    workflow_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    workflow = _get_owned_development_workflow(workflow_id, current_user.id, db)
    return _development_workflow_response(workflow)


@app.post("/api/development/workflows/{workflow_id}/test-results")
async def submit_development_test_result(
    workflow_id: int,
    payload: schemas.DevelopmentTestResult,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    workflow = _get_owned_development_workflow(workflow_id, current_user.id, db)
    if workflow.status not in {"awaiting_tests", "awaiting_retest"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This workflow is not waiting for a test result.",
        )
    if workflow.test_attempts >= 5:
        workflow.status = "blocked"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The workflow reached its five-attempt test limit.",
        )

    attempt = workflow.test_attempts + 1
    prior_status = workflow.status
    workflow.status = "processing_tests"
    db.commit()
    test_context = (
        f"Integration plan:\n{workflow.agent_outputs.get('integration', '')}\n\n"
        f"Actual test result supplied by the user (attempt {attempt}):\n{payload.summary}"
    )
    try:
        test_assessment = await development_workflow_agents.run_followup_agent(
            role="Testing Agent",
            task=workflow.task_description,
            context=test_context
            + "\n\nAssess the supplied test evidence, identify gaps, and state clearly "
            "that you did not run the tests yourself.",
        )
        if payload.passed:
            deployment_plan = await development_workflow_agents.run_followup_agent(
                role="Deployment Agent",
                task=workflow.task_description,
                context=(
                    f"Test assessment:\n{test_assessment}\n\n"
                    "Prepare a deployment checklist and rollback considerations. "
                    "Do not deploy or claim deployment has occurred."
                ),
            )
            debug_output = None
        else:
            deployment_plan = None
            debug_output = await development_workflow_agents.run_followup_agent(
                role="Debugging Agent",
                task=workflow.task_description,
                context=(
                    f"Integration plan:\n{workflow.agent_outputs.get('integration', '')}\n\n"
                    f"Testing assessment:\n{test_assessment}\n\n"
                    f"Test failure evidence:\n{payload.summary}\n\n"
                    "Diagnose likely causes and propose minimal fixes. Do not edit files "
                    "or claim fixes were applied."
                ),
            )
    except RuntimeError as error:
        workflow.status = prior_status
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    workflow.test_attempts = attempt
    workflow.test_results = [
        *workflow.test_results,
        {"attempt": attempt, "passed": payload.passed, "summary": payload.summary},
    ]
    workflow.agent_outputs = {
        **workflow.agent_outputs,
        "testing": test_assessment,
    }
    if payload.passed:
        workflow.agent_outputs["deployment"] = deployment_plan
        workflow.status = "awaiting_deployment"
    elif attempt >= 5:
        workflow.agent_outputs["debugging"] = debug_output
        workflow.status = "blocked"
    else:
        workflow.agent_outputs["debugging"] = debug_output
        workflow.status = "awaiting_retest"
    db.commit()
    db.refresh(workflow)
    return _development_workflow_response(workflow)


@app.post("/api/development/workflows/{workflow_id}/deployment")
def confirm_development_deployment(
    workflow_id: int,
    payload: schemas.DevelopmentDeploymentConfirmation,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    workflow = _get_owned_development_workflow(workflow_id, current_user.id, db)
    if workflow.status != "awaiting_deployment":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Deployment can only be confirmed after tests pass.",
        )
    workflow.deployment = {
        "confirmed": True,
        "deployment_url": str(payload.deployment_url) if payload.deployment_url else None,
        "notes": payload.notes,
        "confirmed_at": datetime.now(timezone.utc).isoformat(),
    }
    workflow.status = "awaiting_monitoring"
    db.commit()
    db.refresh(workflow)
    return _development_workflow_response(workflow)


@app.post("/api/development/workflows/{workflow_id}/monitoring")
async def submit_development_monitoring_report(
    workflow_id: int,
    payload: schemas.DevelopmentMonitoringReport,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    workflow = _get_owned_development_workflow(workflow_id, current_user.id, db)
    if workflow.status != "awaiting_monitoring":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Monitoring can only be recorded after deployment is confirmed.",
        )
    workflow.status = "processing_monitoring"
    db.commit()
    try:
        assessment = await development_workflow_agents.run_followup_agent(
            role="Monitoring Agent",
            task=workflow.task_description,
            context=(
                f"Deployment:\n{workflow.deployment}\n\n"
                f"Operator-submitted health report ({payload.status}):\n{payload.details}\n\n"
                "Summarize observed signals, risks, and next actions. You do not have "
                "live infrastructure access; do not claim independent monitoring."
            ),
        )
    except RuntimeError as error:
        workflow.status = "awaiting_monitoring"
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error

    workflow.monitoring = {
        "status": payload.status,
        "details": payload.details,
        "agent_assessment": assessment,
        "reported_at": datetime.now(timezone.utc).isoformat(),
    }
    workflow.status = "completed" if payload.status == "healthy" else "degraded"
    workflow.agent_outputs = {
        **workflow.agent_outputs,
        "monitoring": assessment,
    }
    db.commit()
    db.refresh(workflow)
    return _development_workflow_response(workflow)


@app.post("/api/auth/register", status_code=status.HTTP_201_CREATED)
@app.post("/auth/signup", status_code=status.HTTP_201_CREATED)
def register_user(payload: schemas.UserCreate, db: Session = Depends(database.get_db)):
    existing_user = db.scalar(select(models.User).where(models.User.email == payload.email))
    if existing_user:
        raise HTTPException(status_code=400, detail="Email is already registered.")

    user = models.User(
        username=payload.username,
        email=payload.email,
        password_hash=auth_utils.hash_password(payload.password),
        gender=payload.gender,
        role="admin" if payload.email in _configured_emails("SUPER_ADMIN_EMAILS") else "user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "User registered successfully", **_token_response(user)}


@app.post("/api/auth/login")
@app.post("/auth/login")
def login_user(payload: schemas.UserLogin, db: Session = Depends(database.get_db)):
    user = db.scalar(select(models.User).where(models.User.email == payload.email))
    if not user or not auth_utils.verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return {"message": "Login successful", **_token_response(user)}


@app.post("/api/users/me/password")
def change_my_password(
    payload: schemas.PasswordChangeRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    if not auth_utils.verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    if auth_utils.verify_password(payload.new_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Choose a new password that differs from your current password.",
        )

    current_user.password_hash = auth_utils.hash_password(payload.new_password)
    db.commit()
    return {"message": "Password changed successfully."}


@app.get("/api/users/me")
def get_my_profile(
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    return {
        **current_user.to_public_dict(),
        "is_super_admin": _is_super_admin(current_user),
    }


@app.patch("/api/users/me")
def update_my_profile(
    payload: schemas.UserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No profile fields were provided.")
    if any(updates.get(field) is None for field in ("username", "email") if field in updates):
        raise HTTPException(
            status_code=422,
            detail="Username and email cannot be null.",
        )
    if "email" in updates:
        existing_user = db.scalar(
            select(models.User).where(
                models.User.email == updates["email"],
                models.User.id != current_user.id,
            )
        )
        if existing_user:
            raise HTTPException(status_code=409, detail="Email is already registered.")
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user.to_public_dict()


@app.get("/api/users/me/candidate-profile")
def get_my_candidate_profile(
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    profile = current_user.candidate_profile
    return _candidate_profile_payload(profile)


@app.put("/api/users/me/candidate-profile")
def update_my_candidate_profile(
    payload: schemas.CandidateProfile,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    profile = current_user.candidate_profile
    values = payload.model_dump()
    if profile is None:
        profile = models.CandidateProfile(user_id=current_user.id, **values)
        db.add(profile)
    else:
        for field, value in values.items():
            setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return {**_candidate_profile_payload(profile), "updated_at": profile.updated_at.isoformat()}


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
@app.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    payload: dict = Depends(auth_utils.get_current_token_payload),
    db: Session = Depends(database.get_db),
):
    auth_utils.revoke_access_token(payload, db)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/auth/google")
async def google_login(data: schemas.GoogleLoginRequest, db: Session = Depends(database.get_db)):
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    try:
        identity = id_token.verify_oauth2_token(data.token, google_requests.Request(), client_id)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid Google token.") from error

    email = identity.get("email")
    if not email or not identity.get("email_verified", False):
        raise HTTPException(status_code=400, detail="Google email is not verified.")

    user = db.scalar(select(models.User).where(models.User.email == email))
    if not user:
        user = models.User(
            username=identity.get("name") or email.split("@")[0],
            email=email.strip().lower(),
            password_hash=auth_utils.hash_password(os.urandom(32).hex()),
            role=(
                "admin"
                if email.strip().casefold()
                in _configured_emails("SUPER_ADMIN_EMAILS")
                else "user"
            ),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return _token_response(user)


@app.get("/users/stats")
async def get_user_stats(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    sessions = db.scalars(
        select(models.InterviewSession).where(models.InterviewSession.user_id == current_user.id)
    ).all()
    scores = [s.average_score for s in sessions if s.average_score is not None]
    return {
        "total_interviews": len(sessions),
        "avg_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
    }


@app.get("/api/billing/subscription")
def get_my_subscription(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    subscription = get_active_subscription(db, current_user.id)
    plan = normalize_plan(subscription.plan) if subscription else "free"
    quotas = PLAN_QUOTAS[plan]
    saved_interviews = db.scalar(
        select(func.count())
        .select_from(models.InterviewSession)
        .where(
            models.InterviewSession.user_id == current_user.id,
            models.InterviewSession.created_at >= _utc_month_start(),
        )
    ) or 0
    interview_count = max(
        saved_interviews,
        _monthly_usage_count(db, current_user.id, "interview"),
    )
    resume_analysis_count = _monthly_usage_count(
        db, current_user.id, "resume_analysis"
    )
    company_question_count = _monthly_usage_count(
        db, current_user.id, "company_question"
    )

    def limit_label(limit: int | None, *, zero_label: str | None = None) -> str:
        if limit is None:
            return "unlimited"
        if limit == 0 and zero_label:
            return zero_label
        return f"{limit} per month"

    response = {
        "plan": plan,
        "status": subscription.status if subscription else "active",
        "interview_limit": limit_label(quotas["interviews"]),
        "interviews_used": interview_count,
        "interviews_remaining": (
            None
            if quotas["interviews"] is None
            else max(0, quotas["interviews"] - interview_count)
        ),
        "resume_analysis_limit": limit_label(quotas["resume_analyses"]),
        "resume_analyses_used": resume_analysis_count,
        "resume_analyses_remaining": (
            None
            if quotas["resume_analyses"] is None
            else max(0, quotas["resume_analyses"] - resume_analysis_count)
        ),
        "company_question_limit": limit_label(
            quotas["company_questions"], zero_label="not included"
        ),
        "company_questions_used": company_question_count,
        "company_questions_remaining": (
            None
            if quotas["company_questions"] is None
            else max(0, quotas["company_questions"] - company_question_count)
        ),
        "resume_build_limit": (
            "unlimited"
            if plan in {"legacy_resume", "elite"}
            else FREE_RESUME_BUILD_LIMIT
        ),
    }
    if subscription:
        response.update({
            "started_at": subscription.started_at.isoformat(),
            "expires_at": subscription.expires_at.isoformat(),
        })
    return response


@app.post("/api/billing/checkout")
def create_upi_checkout(
    payload: schemas.SubscriptionCheckoutRequest,
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    del current_user
    upi_id = os.getenv("UPI_ID", "").strip()
    payee_name = os.getenv("UPI_PAYEE_NAME", "InterviewAI").strip()
    if not upi_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="UPI payments are not configured.",
        )
    payment_uri = build_upi_payment_uri(payload.plan, upi_id, payee_name)
    qr_image = qrcode.make(payment_uri, image_factory=qrcode.image.svg.SvgPathImage)
    qr_buffer = BytesIO()
    qr_image.save(qr_buffer)
    return {
        "plan": payload.plan,
        "amount_rupees": PLAN_PRICES_RUPEES[payload.plan],
        "currency": "INR",
        "upi_id": upi_id,
        "payee_name": payee_name,
        "payment_uri": payment_uri,
        "qr_svg_base64": base64.b64encode(qr_buffer.getvalue()).decode("ascii"),
        "instructions": "Complete payment in your UPI app, then upload the receipt for review.",
    }


@app.post("/api/billing/payments", status_code=status.HTTP_201_CREATED)
async def submit_payment_proof(
    plan: str = Form(...),
    screenshot: UploadFile = File(...),
    transaction_reference: str | None = Form(None, max_length=120),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    if plan not in PLAN_PRICES_RUPEES:
        raise HTTPException(status_code=422, detail="Choose the Pro or Elite plan.")
    content_type = (screenshot.content_type or "").lower()
    allowed_signatures = {
        "image/png": lambda data: data.startswith(b"\x89PNG\r\n\x1a\n"),
        "image/jpeg": lambda data: data.startswith(b"\xff\xd8\xff"),
        "image/webp": lambda data: (
            len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP"
        ),
    }
    if not screenshot.filename or Path(screenshot.filename).suffix.lower() not in {
        ".png", ".jpg", ".jpeg", ".webp"
    } or content_type not in allowed_signatures:
        raise HTTPException(
            status_code=400,
            detail="Payment proof must be a PNG, JPEG, or WebP image.",
        )
    screenshot_data = await screenshot.read(MAX_PAYMENT_SCREENSHOT_SIZE_BYTES + 1)
    if len(screenshot_data) > MAX_PAYMENT_SCREENSHOT_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Payment proof exceeds the 5 MB limit.")
    if not allowed_signatures[content_type](screenshot_data):
        raise HTTPException(
            status_code=400,
            detail="Payment proof content does not match its image type.",
        )

    clean_reference = transaction_reference.strip() if transaction_reference else None
    if clean_reference and db.scalar(
        select(models.PaymentSubmission.id).where(
            func.lower(models.PaymentSubmission.transaction_reference)
            == clean_reference.casefold()
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This UPI transaction reference has already been submitted.",
        )

    payment = models.PaymentSubmission(
        user_id=current_user.id,
        plan=plan,
        amount_rupees=PLAN_PRICES_RUPEES[plan],
        transaction_reference=clean_reference or None,
        screenshot=screenshot_data,
        screenshot_content_type=content_type,
    )
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return {
        "payment_id": payment.id,
        "plan": normalize_plan(payment.plan),
        "amount_rupees": payment.amount_rupees,
        "transaction_reference": payment.transaction_reference,
        "status": payment.status,
        "submitted_at": payment.submitted_at.isoformat(),
    }


@app.get("/api/billing/payments")
def get_my_payment_submissions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    payments = db.scalars(
        select(models.PaymentSubmission)
        .where(models.PaymentSubmission.user_id == current_user.id)
        .order_by(models.PaymentSubmission.submitted_at.desc())
    ).all()
    return [
        {
            "payment_id": payment.id,
            "plan": normalize_plan(payment.plan),
            "amount_rupees": payment.amount_rupees,
            "transaction_reference": payment.transaction_reference,
            "status": payment.status,
            "review_note": payment.review_note,
            "submitted_at": payment.submitted_at.isoformat(),
            "reviewed_at": (
                payment.reviewed_at.isoformat() if payment.reviewed_at else None
            ),
        }
        for payment in payments
    ]


@app.get("/api/admin/summary")
def get_admin_summary(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_admin(current_user)
    now = datetime.now(timezone.utc)
    return {
        "total_users": db.scalar(select(func.count()).select_from(models.User)) or 0,
        "active_subscriptions": db.scalar(
            select(func.count())
            .select_from(models.Subscription)
            .where(
                models.Subscription.status == "active",
                models.Subscription.expires_at > now,
            )
        ) or 0,
        "pending_payments": db.scalar(
            select(func.count())
            .select_from(models.PaymentSubmission)
            .where(models.PaymentSubmission.status == "pending")
        ) or 0,
        "saved_resumes": db.scalar(
            select(func.count()).select_from(models.ResumeDocument)
        ) or 0,
    }


@app.get("/api/admin/users")
def get_admin_users(
    search: str = Query(default="", max_length=120),
    limit: int = Query(default=100, ge=1, le=250),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_admin(current_user)
    query = select(models.User).order_by(models.User.created_at.desc())
    user_filters = []
    clean_search = search.strip()
    if clean_search:
        escaped = clean_search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        user_filters.append(
            models.User.email.ilike(f"%{escaped}%", escape="\\")
            | models.User.username.ilike(f"%{escaped}%", escape="\\")
        )
        query = query.where(*user_filters)
    users = db.scalars(query.offset(offset).limit(limit)).all()
    user_ids = [user.id for user in users]
    if not user_ids:
        total = db.scalar(
            select(func.count()).select_from(models.User).where(*user_filters)
        ) or 0
        return {"users": [], "total": total}
    access_controls = {
        item.user_id: item
        for item in db.scalars(
            select(models.UserAccessControl).where(
                models.UserAccessControl.user_id.in_(user_ids)
            )
        ).all()
    }
    now = datetime.now(timezone.utc)
    subscriptions = db.scalars(
        select(models.Subscription)
        .where(
            models.Subscription.user_id.in_(user_ids),
            models.Subscription.status == "active",
            models.Subscription.expires_at > now,
        )
        .order_by(models.Subscription.expires_at.desc())
    ).all()
    active_subscriptions = {}
    for subscription in subscriptions:
        active_subscriptions.setdefault(subscription.user_id, subscription)
    total = db.scalar(
        select(func.count()).select_from(models.User).where(*user_filters)
    ) or 0
    return {
        "users": [
            _admin_user_payload(
                user,
                access_controls.get(user.id),
                active_subscriptions.get(user.id),
            )
            for user in users
        ],
        "total": total,
    }


@app.patch("/api/admin/users/{user_id}")
def update_admin_user(
    user_id: int,
    payload: schemas.AdminUserUpdate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_admin(current_user)
    if (
        payload.suspended is None
        and payload.plan is None
        and payload.role is None
    ):
        raise HTTPException(
            status_code=422,
            detail="Provide a role, suspension, or plan change.",
        )
    if payload.role is not None:
        _require_super_admin(current_user)
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if _is_super_admin(user) and (
        payload.role == "user" or payload.suspended is True
    ):
        raise HTTPException(
            status_code=409,
            detail="Super-admin accounts cannot be demoted or suspended here.",
        )
    if user.role == "admin" and not _is_super_admin(current_user):
        raise HTTPException(
            status_code=403,
            detail="Only a super-admin can manage another admin account.",
        )

    if payload.role is not None:
        user.role = payload.role
    if payload.suspended is not None:
        access_control = db.get(models.UserAccessControl, user_id)
        if access_control is None:
            access_control = models.UserAccessControl(
                user_id=user_id,
                suspended=payload.suspended,
                updated_by=current_user.email,
                updated_at=datetime.now(timezone.utc),
            )
            db.add(access_control)
        else:
            access_control.suspended = payload.suspended
            access_control.updated_by = current_user.email
            access_control.updated_at = datetime.now(timezone.utc)

    if payload.plan is not None:
        subscriptions = db.scalars(
            select(models.Subscription).where(
                models.Subscription.user_id == user_id,
                models.Subscription.status == "active",
            )
        ).all()
        for subscription in subscriptions:
            subscription.status = "expired"
        if payload.plan != "free":
            now = datetime.now(timezone.utc)
            db.add(
                models.Subscription(
                    user_id=user_id,
                    plan=payload.plan,
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=payload.duration_days),
                )
            )

    db.commit()
    db.refresh(user)
    return _admin_user_payload(
        user,
        db.get(models.UserAccessControl, user.id),
        get_active_subscription(db, user.id),
    )


@app.delete("/api/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(
    user_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_admin(current_user)
    user = db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if (
        user.id == current_user.id
        or _is_super_admin(user)
        or (user.role == "admin" and not _is_super_admin(current_user))
    ):
        raise HTTPException(
            status_code=409,
            detail="You cannot delete your own account or an admin account.",
        )

    session_ids = db.scalars(
        select(models.InterviewSession.id).where(
            models.InterviewSession.user_id == user_id
        )
    ).all()
    if session_ids:
        db.execute(
            sql_delete(models.UserAnswer).where(
                models.UserAnswer.session_id.in_(session_ids)
            )
        )
        db.execute(
            sql_delete(models.CodingRoundLedger).where(
                models.CodingRoundLedger.session_id.in_(session_ids)
            )
        )
    db.execute(
        sql_delete(models.CodingRoundLedger).where(
            models.CodingRoundLedger.user_id == user_id
        )
    )
    db.execute(
        sql_delete(models.InterviewSession).where(
            models.InterviewSession.user_id == user_id
        )
    )
    for model in (
        models.DevelopmentWorkflow,
        models.ResumeDocument,
        models.PaymentSubmission,
        models.Subscription,
        models.CandidateProfile,
        models.UserAccessControl,
    ):
        db.execute(sql_delete(model).where(model.user_id == user_id))
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/admin/payments/pending")
def get_pending_payment_submissions(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_payment_reviewer(current_user)
    payments = db.scalars(
        select(models.PaymentSubmission)
        .where(models.PaymentSubmission.status == "pending")
        .order_by(models.PaymentSubmission.submitted_at)
    ).all()
    return [
        {
            "payment_id": payment.id,
            "user_id": payment.user_id,
            "email": payment.user.email,
            "plan": normalize_plan(payment.plan),
            "amount_rupees": payment.amount_rupees,
            "transaction_reference": payment.transaction_reference,
            "submitted_at": payment.submitted_at.isoformat(),
        }
        for payment in payments
    ]


@app.get("/api/admin/payments/{payment_id}/receipt")
def get_payment_receipt(
    payment_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_payment_reviewer(current_user)
    payment = db.get(models.PaymentSubmission, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment submission not found.")
    return Response(
        content=payment.screenshot,
        media_type=payment.screenshot_content_type,
        headers={"Content-Disposition": f'inline; filename="payment-{payment.id}"'},
    )


@app.post("/api/admin/payments/{payment_id}/review")
def review_payment_submission(
    payment_id: int,
    payload: schemas.PaymentReviewRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_payment_reviewer(current_user)
    payment = db.get(models.PaymentSubmission, payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment submission not found.")
    if payment.status != "pending":
        raise HTTPException(status_code=409, detail="Payment submission was already reviewed.")

    review_note = payload.review_note.strip() if payload.review_note else None
    if payload.decision == "approved":
        try:
            duration_days = int(os.getenv("SUBSCRIPTION_DURATION_DAYS", "30"))
        except ValueError as error:
            raise HTTPException(
                status_code=503, detail="Subscription duration is misconfigured."
            ) from error
        if duration_days < 1:
            raise HTTPException(
                status_code=503, detail="Subscription duration must be at least one day."
            )
        subscription = activate_subscription(
            db, payment, current_user.email, review_note, duration_days
        )
    else:
        subscription = None
        payment.status = "rejected"
        payment.review_note = review_note
        payment.reviewer_email = current_user.email
        payment.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    return {
        "payment_id": payment.id,
        "status": payment.status,
        "review_note": payment.review_note,
        "subscription": (
            {
                "plan": normalize_plan(subscription.plan),
                "expires_at": subscription.expires_at.isoformat(),
            }
            if subscription
            else None
        ),
    }


# ==========================================
# MODULE 2 & 3: QUESTION BANK & METADATA
# ==========================================

@app.get("/api/questions", response_model=list[schemas.QuestionOut])
def get_questions_bank(
    role: str,
    difficulty: str,
    category: str = "Technical",
    db: Session = Depends(database.get_db),
    _: models.User = Depends(auth_utils.get_current_user)
):
    questions = db.scalars(
        select(models.Question).where(
            models.Question.role.ilike(f"%{role}%"),
            models.Question.difficulty.ilike(f"%{difficulty}%"),
            models.Question.category.ilike(f"%{category}%")
        )
    ).all()

    return [
        schemas.QuestionOut(
            id=q.id,
            role=q.role,
            category=q.category,
            difficulty=q.difficulty,
            question_text=q.question_text,
            key_concepts=[k.strip() for k in q.key_concepts.split(",") if k.strip()]
        )
        for q in questions
    ]


@app.get("/interviews/companies/suggestions")
async def get_company_suggestions(_: models.User = Depends(auth_utils.get_current_user)):
    suggestions = set(get_company_intelligence().get_all_companies())
    data_dir = Path(__file__).parent / "data"
    for filename in ("discoveries.json", "stealth_registry.json"):
        path = data_dir / filename
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if filename == "discoveries.json" and isinstance(data, list):
            suggestions.update(item["company_name"] for item in data if isinstance(item, dict) and item.get("company_name"))
        elif isinstance(data, dict):
            suggestions.update(data.keys())
    return sorted(c for c in suggestions if isinstance(c, str) and c.strip())


@app.get("/api/companies/discoveries")
def list_company_discoveries(
    _: models.User = Depends(auth_utils.get_current_user),
):
    entries: dict[tuple[str, str], dict] = {}
    tier_priority = {"curated": 3, "discovery": 2, "stealth": 1}

    def add_entry(name: str, profile: dict, tier: str) -> None:
        clean_name = name.strip()
        if not clean_name:
            return
        geography = profile.get("geography")
        key = (clean_name.casefold(), str(geography or "").casefold())
        existing = entries.get(key)
        if existing and tier_priority[existing["source_tier"]] > tier_priority[tier]:
            return
        entries[key] = {
            "company_name": clean_name,
            "industry": profile.get("industry"),
            "geography": geography,
            "interview_style": profile.get("interview_style"),
            "difficulty_level": profile.get("difficulty_level"),
            "cultural_values": profile.get("cultural_values", []),
            "interview_rounds": profile.get("interview_rounds", {}),
            "tips": profile.get("tips", []),
            "confidence_score": profile.get("confidence_score", 100 if tier == "curated" else 0),
            "is_synthetic": bool(profile.get("is_synthetic", tier == "stealth")),
            "sources": profile.get("sources", []),
            "source_tier": tier,
        }

    for name in get_company_intelligence().get_all_companies():
        profile = get_company_intelligence().get_company(name) or {}
        add_entry(name, profile, "curated")

    data_dir = Path(__file__).parent / "data"
    for filename, tier in (("discoveries.json", "discovery"), ("stealth_registry.json", "stealth")):
        path = data_dir / filename
        if not path.exists():
            continue
        try:
            stored = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            logger.exception("Could not load company intelligence file %s", path)
            raise HTTPException(
                status_code=500,
                detail=f"Could not load the {tier} company registry.",
            ) from error
        if filename == "discoveries.json":
            if isinstance(stored, list):
                for item in stored:
                    if not isinstance(item, dict):
                        continue
                    profile = item.get("profile", item.get("interview_intelligence_profile", item))
                    if isinstance(profile, dict):
                        add_entry(
                            str(item.get("company_name") or profile.get("company_name") or profile.get("company") or ""),
                            profile,
                            "discovery",
                        )
            elif isinstance(stored, dict):
                for name, profile in stored.items():
                    if isinstance(profile, dict):
                        add_entry(str(profile.get("company_name") or name), profile, "discovery")
            else:
                raise HTTPException(status_code=500, detail="The discovery registry has an invalid shape.")
        elif isinstance(stored, dict):
            for name, profile in stored.items():
                if isinstance(profile, dict):
                    add_entry(str(profile.get("company_name") or profile.get("name") or name), profile, "stealth")
        else:
            raise HTTPException(status_code=500, detail="The stealth registry has an invalid shape.")

    return {
        "total": len(entries),
        "companies": sorted(
            entries.values(),
            key=lambda item: (item["company_name"].casefold(), str(item["geography"] or "").casefold()),
        ),
    }


@app.post("/api/companies/discoveries", status_code=status.HTTP_202_ACCEPTED)
async def start_company_discovery(
    payload: schemas.CompanyDiscoveryRequest,
    _: models.User = Depends(auth_utils.get_current_user),
):
    service = get_intelligence_service()
    return await service.start_discovery(
        payload.company,
        payload.job_description,
        payload.geography,
    )


@app.get("/api/companies/discoveries/status")
def get_company_discovery_status(
    company: str,
    geography: str | None = None,
    _: models.User = Depends(auth_utils.get_current_user),
):
    if not company.strip():
        raise HTTPException(status_code=422, detail="Company cannot be blank.")
    return get_intelligence_service().get_discovery_status(company, geography)


@app.get("/api/interviews/rounds")
def get_interview_rounds(
    role: str,
    job_description: str | None = None,
    company_industry: str | None = None,
    _: models.User = Depends(auth_utils.get_current_user),
):
    rounds = get_rounds_for_role(role, job_description, company_industry)
    return [
        {"name": name, **get_round_config(name)}
        for name in rounds
    ]


# ==========================================
# MODULE 4 & 5: SESSIONS & EVALUATION
# ==========================================


def _session_practice_question_ids(session: models.InterviewSession) -> list[int]:
    if not session.transcript or session.transcript[0].get("role") != "system":
        return []
    question_ids = session.transcript[0].get("practice_question_ids", [])
    return [int(question_id) for question_id in question_ids]


def _session_questions_per_round(session: models.InterviewSession) -> int:
    transcript = session.transcript
    if transcript and isinstance(transcript[0], dict) and transcript[0].get("role") == "system":
        configured_count = transcript[0].get("questions_per_round")
        if configured_count in {5, 10, 20}:
            return configured_count
    return get_round_config(session.interview_round)["max_questions"]


def _practice_question_payload(question: models.Question) -> dict:
    return {
        "id": question.id,
        "role": question.role,
        "category": question.category,
        "difficulty": question.difficulty,
        "question_text": question.question_text,
        "key_concepts": [
            concept.strip()
            for concept in question.key_concepts.split(",")
            if concept.strip()
        ],
    }


@app.post("/api/practice/start", status_code=status.HTTP_201_CREATED)
def start_question_practice(
    payload: schemas.PracticeCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    questions = db.scalars(
        select(models.Question)
        .where(
            models.Question.role.ilike(f"%{payload.role.strip()}%"),
            models.Question.difficulty.ilike(f"%{payload.difficulty.strip()}%"),
            models.Question.category.ilike(f"%{payload.category.strip()}%"),
        )
        .order_by(models.Question.id)
        .limit(100)
    ).all()
    if not questions:
        raise HTTPException(
            status_code=404,
            detail="No questions match the selected role, difficulty, and category.",
        )
    question_ids = [question.id for question in questions]
    first_question = questions[0]
    session = models.InterviewSession(
        user_id=current_user.id,
        role_category=payload.role.strip(),
        sub_role=payload.role.strip(),
        difficulty=payload.difficulty.strip(),
        category=payload.category.strip(),
        interview_round="Question Practice",
        overall_status="in_progress",
        transcript=[
            {"role": "system", "practice_question_ids": question_ids},
            {
                "role": "assistant",
                "content": first_question.question_text,
                "question_id": first_question.id,
            },
        ],
    )
    usage_id = _reserve_interview_quota(db, current_user)
    db.add(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _release_monthly_usage(db, usage_id)
        raise
    db.refresh(session)
    return {
        "interview_id": session.id,
        "total_questions": len(questions),
        "question": _practice_question_payload(first_question),
    }


@app.post("/api/practice/answer")
async def submit_practice_answer(
    payload: schemas.PracticeAnswerSubmit,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == payload.interview_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Practice session not found.")
    if session.overall_status != "in_progress":
        raise HTTPException(status_code=409, detail="This practice session has ended.")

    question_ids = _session_practice_question_ids(session)
    if not question_ids:
        raise HTTPException(status_code=409, detail="Practice questions are unavailable.")
    current_question_id = next(
        (
            int(item["question_id"])
            for item in reversed(session.transcript)
            if item.get("role") == "assistant" and item.get("question_id") is not None
        ),
        None,
    )
    question_id = payload.question_id or current_question_id
    if question_id is None or question_id not in question_ids:
        raise HTTPException(
            status_code=400,
            detail="Question does not belong to this practice session.",
        )
    question = db.get(models.Question, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Practice question no longer exists.")

    evaluation = await run_in_threadpool(
        evaluate_answer_nlp,
        payload.answer,
        question.reference_answer,
        question.key_concepts,
    )
    answer_record = models.UserAnswer(
        session_id=session.id,
        question_id=question.id,
        question_text=question.question_text,
        user_answer=payload.answer,
        similarity_score=evaluation["similarity_score"],
        keyword_score=evaluation["keyword_score"],
        final_score=evaluation["final_score"],
        missing_concepts=", ".join(evaluation["missing_concepts"]),
        feedback=evaluation["feedback"],
    )
    db.add(answer_record)

    is_current_question = question.id == current_question_id
    next_question = None
    if is_current_question:
        position = question_ids.index(question.id)
        if position + 1 < len(question_ids):
            next_question = db.get(models.Question, question_ids[position + 1])
            if next_question is not None:
                session.transcript = [
                    *session.transcript,
                    {"role": "user", "content": payload.answer, "question_id": question.id},
                    {
                        "role": "assistant",
                        "content": next_question.question_text,
                        "question_id": next_question.id,
                    },
                ]
                session.questions_count += 1
        else:
            session.transcript = [
                *session.transcript,
                {"role": "user", "content": payload.answer, "question_id": question.id},
            ]
            session.questions_count += 1
            session.overall_status = "completed"
    else:
        next_question = db.get(models.Question, current_question_id)
        session.transcript = [
            *session.transcript,
            {
                "role": "user",
                "content": payload.answer,
                "question_id": question.id,
                "retry": True,
            },
        ]

    session.total_questions += 1
    session.average_score = (
        (session.average_score * (session.total_questions - 1) + evaluation["final_score"])
        / session.total_questions
    )
    session.score = evaluation["final_score"]
    db.commit()
    db.refresh(answer_record)

    return {
        "answer_id": answer_record.id,
        "question_id": question.id,
        "evaluation": evaluation,
        "reference_answer": question.reference_answer,
        "next_question": (
            {
                "id": next_question.id,
                "question_text": next_question.question_text,
            }
            if next_question
            else None
        ),
        "retry": not is_current_question,
        "session_completed": session.overall_status == "completed",
        "questions_answered": session.questions_count,
        "total_questions": len(question_ids),
    }


async def _create_interview(
    *,
    db: Session,
    current_user: models.User,
    role_category: str,
    sub_role: str,
    difficulty_level: int,
    target_company: str | None,
    target_geography: str | None,
    is_panel: bool,
    job_description: str | None,
    interviewer_name: str,
    questions_per_round: int = 20,
    resume_text: str | None = None,
    resume_analysis: dict | str | None = None,
    candidate_profile: models.CandidateProfile | None = None,
    technical_categories: list[str] | None = None,
):
    candidate_profile = candidate_profile or current_user.candidate_profile
    if target_company and target_company.strip():
        _require_plan(db, current_user, "pro")
    if job_description and job_description.strip():
        _require_plan(db, current_user, "pro")
    if is_panel:
        _require_plan(db, current_user, "elite")

    company_intel = await _get_company_intelligence(
        target_company, job_description, target_geography
    )
    company_industry = (
        company_intel.get("industry") if isinstance(company_intel, dict) else None
    )
    interview_round = get_first_round(
        role_category, difficulty_level, job_description, company_industry
    )
    try:
        category_plan = shuffled_category_plan(
            resolve_technical_categories(
                technical_categories,
                resume_text=resume_text,
                role=f"{role_category} {sub_role}",
            )
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    profile_context = _candidate_profile_context(candidate_profile)
    persisted_context = {
        "technical_category_plan": category_plan,
        "questions_per_round": questions_per_round,
    }
    if profile_context:
        persisted_context["candidate_profile"] = _candidate_profile_payload(candidate_profile)
    if company_intel:
        persisted_context["company_intelligence"] = (
            json.dumps(company_intel, ensure_ascii=True, default=str)[:3000]
            if isinstance(company_intel, dict)
            else str(company_intel)[:3000]
        )
    
    first_question_category = (
        category_plan[0] if "technical" in interview_round.casefold() else None
    )
    interview_usage_id = _reserve_interview_quota(db, current_user)
    company_question_usage_id = None
    try:
        if target_company and target_company.strip():
            _, company_question_usage_id = _reserve_monthly_usage(
                db, current_user, "company_question", required=True
            )
    except Exception:
        _release_monthly_usage(db, interview_usage_id)
        raise
    try:
        first_question = await gemini_service.generate_interview_question(
            role=role_category,
            sub_role=sub_role,
            difficulty=difficulty_level,
            company=target_company,
            round_name=interview_round,
            is_panel=is_panel,
            jd=job_description,
            resume_text=chunk_resume_context(resume_text) if resume_text else None,
            current_time=datetime.now(timezone.utc).isoformat(),
            interviewer_name=interviewer_name,
            company_intel=company_intel,
            round_criteria=[
                *get_round_config(interview_round)["evaluation_criteria"],
                *(
                    [f"Focus this question on the {first_question_category} category."]
                    if first_question_category
                    else []
                ),
            ],
            candidate_context=profile_context,
            question_category=first_question_category,
        )
    except Exception:
        _release_monthly_usage(db, company_question_usage_id)
        _release_monthly_usage(db, interview_usage_id)
        raise
    
    difficulty_map = {1: "Beginner", 2: "Beginner", 3: "Intermediate", 4: "Advanced", 5: "Advanced"}
    difficulty_str = difficulty_map.get(difficulty_level, "Intermediate")

    session = models.InterviewSession(
        user_id=current_user.id,
        role_category=role_category,
        sub_role=sub_role,
        difficulty_level=difficulty_level,
        difficulty=difficulty_str,
        category="HR" if "hr" in role_category.lower() else "Technical",
        target_company=target_company,
        is_panel=is_panel,
        interviewer_name=interviewer_name,
        job_description=job_description,
        resume_text=resume_text,
        resume_analysis=resume_analysis if isinstance(resume_analysis, dict) else None,
        interview_round=interview_round,
        transcript=[
            *([{"role": "system", **persisted_context}] if persisted_context else []),
            {
                "role": "assistant",
                "content": first_question,
                "round": interview_round,
                "technical_category": first_question_category,
                "target_geography": target_geography,
            }
        ],
    )
    db.add(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        _release_monthly_usage(db, company_question_usage_id)
        _release_monthly_usage(db, interview_usage_id)
        raise
    db.refresh(session)
    return {
        "id": session.id,
        "role_category": session.role_category,
        "sub_role": session.sub_role,
        "difficulty_level": session.difficulty_level,
        "difficulty": session.difficulty,
        "target_company": session.target_company,
        "target_geography": target_geography,
        "interviewer_name": session.interviewer_name,
        "first_question": first_question,
        "question_category": first_question_category,
        "technical_category_plan": category_plan,
        "questions_per_round": questions_per_round,
        "resume_analysis": resume_analysis,
        "company_intelligence": company_intel,
        "created_at": session.created_at,
        "questions_asked": 0,
        "total_questions": 0,
        "questions_per_round": questions_per_round,
    }


@app.post("/interviews/upload-resume")
async def upload_resume(
    file: UploadFile = File(...),
    role_category: str = Form(...),
    sub_role: str = Form(...),
    difficulty_level: int = Form(1),
    target_company: str | None = Form(None),
    target_geography: str | None = Form(None),
    is_panel: bool = Form(False),
    job_description: str | None = Form(None),
    interviewer_name: str = Form("Adinath"),
    questions_per_round: int = Form(20),
    technical_categories: list[str] = Form(default=[]),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    if job_description and job_description.strip():
        _require_plan(db, current_user, "pro")
    if is_panel:
        _require_plan(db, current_user, "elite")
    if questions_per_round not in {5, 10, 20}:
        raise HTTPException(
            status_code=422,
            detail="Choose 5, 10, or 20 questions per round.",
        )
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    file_content = await file.read(MAX_RESUME_SIZE_BYTES + 1)
    if len(file_content) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the 10 MB limit.")
    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
    resume_text = await run_in_threadpool(_extract_resume_text, file_content)

    _, usage_id = _reserve_monthly_usage(
        db, current_user, "resume_analysis", required=True
    )
    try:
        analysis = analyze_resume_interview_context(resume_text)
        analysis["ats_analysis"] = analyze_resume_match(resume_text, job_description)

        return await _create_interview(
            db=db,
            current_user=current_user,
            role_category=role_category,
            sub_role=sub_role,
            difficulty_level=difficulty_level,
            target_company=target_company,
            target_geography=target_geography,
            is_panel=is_panel,
            job_description=job_description,
            interviewer_name=interviewer_name,
            questions_per_round=questions_per_round,
            resume_text=resume_text,
            resume_analysis=analysis,
            candidate_profile=current_user.candidate_profile,
            technical_categories=technical_categories,
        )
    except Exception:
        _release_monthly_usage(db, usage_id)
        raise


@app.post("/api/ats/analyze")
async def analyze_ats_score(
    file: UploadFile | None = File(None),
    resume_text: str | None = Form(None),
    job_description: str | None = Form(None),
    target_role: str | None = Form(None),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    extracted_text = (resume_text or "").strip()
    filename = None
    if file and file.filename:
        filename = Path(file.filename).name
        if Path(file.filename).suffix.lower() != ".pdf":
            raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
        content = await file.read(MAX_RESUME_SIZE_BYTES + 1)
        if len(content) > MAX_RESUME_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Resume exceeds the 10 MB limit.")
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
        extracted_text = await run_in_threadpool(_extract_resume_text, content)

    if not extracted_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Please provide a PDF resume or paste your resume text.",
        )

    _, usage_id = _reserve_monthly_usage(
        db, current_user, "resume_analysis", required=True
    )
    try:
        result = await run_in_threadpool(
            calculate_detailed_ats_score,
            resume_text=extracted_text,
            job_description=job_description,
            target_role=target_role,
        )
        result["ai_match_prediction"] = await gemini_service.predict_resume_match(
            resume_text=extracted_text,
            job_description=job_description,
            target_role=target_role,
        )
    except Exception:
        _release_monthly_usage(db, usage_id)
        raise
    if filename:
        result["filename"] = filename
    return result


@app.get("/api/resumes/templates")
def get_resume_templates():
    return list(RESUME_TEMPLATES)


@app.get("/api/resumes")
def get_my_resumes(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    plan = get_user_plan(db, current_user.id)
    build_count = db.scalar(
        select(func.count())
        .select_from(models.ResumeDocument)
        .where(models.ResumeDocument.user_id == current_user.id)
    ) or 0
    resumes = db.scalars(
        select(models.ResumeDocument)
        .where(models.ResumeDocument.user_id == current_user.id)
        .order_by(models.ResumeDocument.updated_at.desc(), models.ResumeDocument.id.desc())
    ).all()
    paid_builder = plan in {"legacy_resume", "elite"}
    return {
        "plan": plan,
        "build_count": build_count,
        "free_build_limit": FREE_RESUME_BUILD_LIMIT,
        "remaining_free_builds": (
            None if paid_builder else max(0, FREE_RESUME_BUILD_LIMIT - build_count)
        ),
        "can_build": paid_builder or build_count < FREE_RESUME_BUILD_LIMIT,
        "can_customize_upload": paid_builder,
        "templates": list(RESUME_TEMPLATES),
        "resumes": [_resume_document_payload(document) for document in resumes],
    }


@app.post("/api/resumes/import")
async def import_resume_for_customization(
    file: UploadFile = File(...),
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_resume_subscription(db, current_user)
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    content = await file.read(MAX_RESUME_UPLOAD_SIZE_BYTES + 1)
    if len(content) > MAX_RESUME_UPLOAD_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the 10 MB limit.")
    if not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
    extracted_text = await run_in_threadpool(_extract_resume_text, content)
    if len(extracted_text) > 30000:
        raise HTTPException(
            status_code=413,
            detail="Extracted resume text exceeds the 30,000 character limit.",
        )
    return {
        "filename": Path(file.filename).name,
        "resume_text": extracted_text,
    }


@app.post("/api/resumes", status_code=status.HTTP_201_CREATED)
def create_resume(
    payload: schemas.ResumeCreateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    template = RESUME_TEMPLATE_BY_ID.get(payload.template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Choose a valid resume template.")

    plan = get_user_plan(db, current_user.id)
    if payload.source == "upload":
        _require_resume_subscription(db, current_user)

    db.scalar(
        select(models.User)
        .where(models.User.id == current_user.id)
        .with_for_update()
    )
    build_count = db.scalar(
        select(func.count())
        .select_from(models.ResumeDocument)
        .where(models.ResumeDocument.user_id == current_user.id)
    ) or 0
    if plan not in {"legacy_resume", "elite"} and build_count >= FREE_RESUME_BUILD_LIMIT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "You have used all 3 free resume builds. Upgrade to Elite "
                "plan to create unlimited resumes."
            ),
        )

    document = models.ResumeDocument(
        user_id=current_user.id,
        template_id=template["id"],
        title=payload.title,
        source=payload.source,
        content=payload.content.model_dump(mode="json"),
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return {
        **_resume_document_payload(document),
        "build_count": build_count + 1,
        "remaining_free_builds": (
            None
            if plan in {"legacy_resume", "elite"}
            else max(0, FREE_RESUME_BUILD_LIMIT - build_count - 1)
        ),
    }


@app.put("/api/resumes/{resume_id}")
def update_resume(
    resume_id: int,
    payload: schemas.ResumeUpdateRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    document = db.scalar(
        select(models.ResumeDocument).where(
            models.ResumeDocument.id == resume_id,
            models.ResumeDocument.user_id == current_user.id,
        )
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Resume not found.")
    if document.source == "upload":
        _require_resume_subscription(db, current_user)
    template = RESUME_TEMPLATE_BY_ID.get(payload.template_id)
    if template is None:
        raise HTTPException(status_code=422, detail="Choose a valid resume template.")

    document.template_id = template["id"]
    document.title = payload.title
    document.content = payload.content.model_dump(mode="json")
    db.commit()
    db.refresh(document)
    return _resume_document_payload(document)


@app.post("/api/resume/analyze")
async def analyze_resume_against_job(
    file: UploadFile = File(...),
    job_description: str = Form(...),
    current_user: models.User = Depends(auth_utils.get_current_user),
    db: Session = Depends(database.get_db),
):
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    file_content = await file.read(MAX_RESUME_SIZE_BYTES + 1)
    if len(file_content) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the 10 MB limit.")
    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
    resume_text = _extract_resume_text(file_content)
    _, usage_id = _reserve_monthly_usage(
        db, current_user, "resume_analysis", required=True
    )
    try:
        return {
            "filename": Path(file.filename).name,
            "detected_skills": await run_in_threadpool(
                parse_resume_skills_from_bytes, file_content
            ),
            **analyze_resume_match(resume_text, job_description),
        }
    except Exception:
        _release_monthly_usage(db, usage_id)
        raise


@app.post("/api/resume/rewrite")
async def rewrite_resume_for_job(
    payload: schemas.ResumeRewriteRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _require_plan(db, current_user, "pro")
    _, usage_id = _reserve_monthly_usage(
        db, current_user, "resume_analysis", required=True
    )
    try:
        rewritten = _decode_model_json(
            await gemini_service.rewrite_resume(
                payload.resume_text, payload.job_description
            )
        )
        changes = rewritten.get("changes")
        if (
            not isinstance(rewritten.get("rewritten_resume"), str)
            or not rewritten["rewritten_resume"].strip()
            or not isinstance(changes, list)
            or any(not isinstance(change, str) for change in changes)
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI service returned an invalid resume rewrite.",
            )
        return {
            "rewritten_resume": rewritten["rewritten_resume"],
            "changes": changes,
            "ats_analysis": analyze_resume_match(
                rewritten["rewritten_resume"], payload.job_description
            ),
        }
    except Exception:
        _release_monthly_usage(db, usage_id)
        raise


@app.post("/interviews/start", response_model=schemas.InterviewResponse)
async def start_interview(
    data: schemas.InterviewCreate,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    return await _create_interview(
        db=db,
        current_user=current_user,
        role_category=data.role_category,
        sub_role=data.sub_role,
        difficulty_level=data.difficulty_level,
        questions_per_round=data.questions_per_round,
        target_company=data.target_company,
        target_geography=data.target_geography,
        is_panel=data.is_panel,
        job_description=data.job_description,
        interviewer_name=data.interviewer_name,
        candidate_profile=current_user.candidate_profile,
        technical_categories=data.technical_categories,
    )


@app.post("/interviews/submit-answer")
async def submit_answer(
    data: schemas.AnswerSubmit,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == data.interview_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if not session:
        raise HTTPException(status_code=404, detail="Interview not found.")
    existing_transcript = session.transcript if isinstance(session.transcript, list) else []
    pending_answer = existing_transcript[-1] if existing_transcript else None
    pending_final_report = (
        session.overall_status == "completed"
        and isinstance(pending_answer, dict)
        and pending_answer.get("role") == "user"
        and pending_answer.get("content") == data.answer
        and pending_answer.get("report_pending") is True
    )
    if session.overall_status != "in_progress" and not pending_final_report:
        raise HTTPException(status_code=409, detail="This interview session has already ended.")

    if pending_final_report:
        company_intel = _session_company_intelligence(session)
        try:
            master_report_raw = await gemini_service.generate_master_report({
                "transcript": existing_transcript,
                "round_scores": session.round_scores,
                "sub_role": session.sub_role,
                "target_company": session.target_company,
                "rounds_completed": session.rounds_completed,
                "required_rounds": list(get_rounds_for_role(
                    session.role_category,
                    session.job_description,
                    company_intel.get("industry") if isinstance(company_intel, dict) else None,
                )),
            })
            master_report = _apply_feedback_tier(
                _validate_hiring_report(_decode_model_json(master_report_raw)),
                get_user_plan(db, current_user.id),
            )
            report_provider_status = gemini_service.generation_status()
        except (RuntimeError, HTTPException):
            logger.exception("Could not generate the completed interview report")
            report_provider_status = gemini_service.generation_status()
            pending_report_answer = {
                **existing_transcript[-1],
                "report_provider_status": report_provider_status,
            }
            session.transcript = [
                *existing_transcript[:-1],
                pending_report_answer,
            ]
            db.commit()
            return {
                "evaluation": pending_answer["evaluation"],
                "ai_provider_status": pending_answer.get("ai_provider_status"),
                "report_provider_status": report_provider_status,
                "master_report": None,
                "master_report_pending": True,
                "next_question": None,
                "terminated": True,
                "round_completed": True,
                "round_passed": True,
                "interview_completed": True,
                "overall_status": "completed",
                "rounds_completed": session.rounds_completed,
                "round_scores": session.round_scores,
                "round_score": round(session.score or 0, 1),
                "questions_asked": session.questions_count,
                "total_questions": session.total_questions,
                "questions_per_round": _session_questions_per_round(session),
                "coding_gate_required": False,
                "behavioral_metrics": pending_answer.get("behavioral_metrics"),
                "overall_message": (
                    "All interview rounds are complete. The final scorecard could not "
                    "be generated yet; retry the scorecard when ready."
                ),
            }
        completed_answer = {**pending_answer}
        completed_answer.pop("report_pending", None)
        completed_answer["master_report"] = master_report
        completed_answer["report_provider_status"] = report_provider_status
        completed_answer["completion"] = {
            "status": "completed",
            "message": "Congratulations! You have completed all interview rounds.",
        }
        session.transcript = [
            *existing_transcript[:-1],
            completed_answer,
        ]
        db.commit()
        await get_memory_service().learn_from_session({
            "target_company": session.target_company,
            "role_category": session.role_category,
            "rounds_completed": session.rounds_completed,
            "score": (
                sum(session.round_scores.values()) / len(session.round_scores)
                if session.round_scores
                else 0
            ),
        })
        return {
            "evaluation": pending_answer["evaluation"],
            "ai_provider_status": pending_answer.get("ai_provider_status"),
            "report_provider_status": report_provider_status,
            "master_report": master_report,
            "next_question": None,
            "terminated": True,
            "round_completed": True,
            "round_passed": True,
            "interview_completed": True,
            "overall_status": "completed",
            "rounds_completed": session.rounds_completed,
            "round_scores": session.round_scores,
            "round_score": round(session.score or 0, 1),
            "questions_asked": session.questions_count,
            "total_questions": session.total_questions,
            "questions_per_round": _session_questions_per_round(session),
            "coding_gate_required": False,
            "behavioral_metrics": pending_answer.get("behavioral_metrics"),
            "overall_message": "Congratulations! You have completed all rounds.",
        }
    has_pending_evaluation = (
        isinstance(pending_answer, dict)
        and pending_answer.get("role") == "user"
        and pending_answer.get("evaluation_pending") is True
    )
    if has_pending_evaluation and pending_answer.get("content") != data.answer:
        behavioral_metrics = analyze_speaking_metrics(
            data.answer, data.answer_duration_seconds
        )
        pending_answer = {
            **pending_answer,
            "content": data.answer,
            "behavioral_metrics": behavioral_metrics,
        }
        existing_transcript = [
            *existing_transcript[:-1],
            pending_answer,
        ]
        session.transcript = existing_transcript
        db.commit()
    if (
        isinstance(pending_answer, dict)
        and pending_answer.get("role") == "user"
        and pending_answer.get("content") == data.answer
        and isinstance(pending_answer.get("evaluation"), dict)
        and session.questions_count < _session_questions_per_round(session)
    ):
        company_intel = _session_company_intelligence(session)
        if company_intel is None and session.target_company:
            company_intel = await _get_company_intelligence(
                session.target_company,
                session.job_description,
                _session_target_geography(session),
            )
        try:
            next_question, next_question_category = await _generate_session_question(
                db,
                session,
                company_intel,
                include_history=not bool(pending_answer.get("round_transition")),
            )
        except AIProviderTimeout as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Your answer was saved and evaluated, but the next question timed out. Submit again to continue.",
                headers={"Retry-After": "5"},
            ) from error
        session.transcript = [
            *existing_transcript,
            {
                "role": "assistant",
                "content": next_question,
                "round": session.interview_round,
                "technical_category": next_question_category,
            },
        ]
        db.commit()
        transition = pending_answer.get("round_transition", {})
        coding_ledger = db.scalar(
            select(models.CodingRoundLedger).where(
                models.CodingRoundLedger.session_id == session.id,
                models.CodingRoundLedger.user_id == current_user.id,
            )
        )
        coding_gate_required = (
            session.interview_round == "Behavioral/HR"
            and "Technical/Screening" in session.rounds_completed
            and (not coding_ledger or coding_ledger.ledger_data.get("status") != "completed")
        )
        return {
            "evaluation": pending_answer["evaluation"],
            "next_question": next_question,
            "question_category": next_question_category,
            "terminated": False,
            "round_completed": bool(transition.get("round_completed")),
            "round_passed": bool(transition.get("round_passed")),
            "next_round": transition.get("next_round"),
            "next_round_number": transition.get("next_round_number"),
            "current_round": session.interview_round,
            "current_round_number": session.current_round_number,
            "rounds_completed": session.rounds_completed,
            "round_scores": session.round_scores,
            "round_score": session.score,
            "questions_asked": session.questions_count,
            "total_questions": session.total_questions,
            "questions_per_round": _session_questions_per_round(session),
            "difficulty_level": session.difficulty_level,
            "difficulty_scaled": bool(transition.get("difficulty_scaled")),
            "coding_gate_required": coding_gate_required,
            "behavioral_metrics": pending_answer.get("behavioral_metrics"),
            "ai_provider_status": pending_answer.get("ai_provider_status"),
        }

    if (
        session.interview_round == "Behavioral/HR"
        and "Technical/Screening" in session.rounds_completed
    ):
        coding_ledger = db.scalar(
            select(models.CodingRoundLedger).where(
                models.CodingRoundLedger.session_id == session.id,
                models.CodingRoundLedger.user_id == current_user.id,
            )
        )
        if not coding_ledger or coding_ledger.ledger_data.get("status") != "completed":
            raise HTTPException(
                status_code=409,
                detail="Complete both coding simulation rounds before continuing to the HR interview.",
            )

    behavioral_metrics = (
        pending_answer.get("behavioral_metrics")
        if has_pending_evaluation
        else analyze_speaking_metrics(data.answer, data.answer_duration_seconds)
    )
    transcript = (
        existing_transcript
        if has_pending_evaluation
        else [
            *existing_transcript,
            {
                "role": "user",
                "content": data.answer,
                "round": session.interview_round,
                "behavioral_metrics": behavioral_metrics,
                "evaluation_pending": True,
            },
        ]
    )
    questions_count = session.questions_count + 1
    round_config = {
        **get_round_config(session.interview_round),
        "max_questions": _session_questions_per_round(session),
    }

    last_question_item = next(
        (
            item
            for item in reversed(existing_transcript)
            if item.get("role") == "assistant"
            and isinstance(item.get("content"), str)
        ),
        None,
    )
    last_question = last_question_item.get("content") if last_question_item else None
    if not last_question:
        raise HTTPException(status_code=409, detail="No preceding question found.")

    if not has_pending_evaluation:
        session.transcript = transcript
        db.commit()

    company_intel = _session_company_intelligence(session)
    if company_intel is None and session.target_company:
        company_intel = await _get_company_intelligence(
            session.target_company,
            session.job_description,
            _session_target_geography(session),
        )
    
    # 1. AI Evaluation
    evaluation_raw = await gemini_service.evaluate_answer(
        question=last_question,
        answer=data.answer,
        role=session.role_category,
        round_name=session.interview_round,
        company=session.target_company,
        company_intel=company_intel,
        round_criteria=[
            *round_config["evaluation_criteria"],
            *(
                [
                    f"Evaluate technical accuracy in the {last_question_item['technical_category']} category."
                ]
                if last_question_item.get("technical_category")
                else []
            ),
        ],
    )
    evaluation_provider_status = gemini_service.generation_status()
    evaluation = _decode_model_json(evaluation_raw)
    current_plan = get_user_plan(db, current_user.id)
    if current_plan == "elite":
        evaluation["vibe_assessment"] = _validate_vibe_assessment(
            evaluation.get("vibe_assessment")
        )
    else:
        evaluation.pop("vibe_assessment", None)
    if "score" not in evaluation:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation did not include a numeric score.",
        )
    try:
        raw_score = float(evaluation["score"])
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation did not include a valid numeric score.",
        ) from error
    if (
        isinstance(evaluation["score"], bool)
        or not math.isfinite(raw_score)
        or not 0 <= raw_score <= 10
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation score must be between 0 and 10.",
        )
    normalized_score = float(max(0.0, min(100.0, raw_score * 10 if raw_score <= 10 else raw_score)))
    evaluation["score"] = round(raw_score, 1)

    bank_question = db.scalar(
        select(models.Question).where(
            models.Question.question_text == last_question
        )
    )
    nlp_evaluation = None
    if bank_question is not None:
        nlp_evaluation = await run_in_threadpool(
            evaluate_answer_nlp,
            data.answer,
            bank_question.reference_answer,
            bank_question.key_concepts,
        )
        evaluation["automated_nlp"] = nlp_evaluation

    # 2. Persist AI and NLP scores separately rather than duplicating the AI score.
    improvements = evaluation.get("improvements", [])
    missing_concepts = (
        nlp_evaluation["missing_concepts"]
        if nlp_evaluation is not None
        else improvements if isinstance(improvements, list) else [str(improvements)]
    )
    if current_plan == "free":
        missing_concepts = []
        evaluation.pop("strengths", None)
        evaluation.pop("improvements", None)
        evaluation.pop("automated_nlp", None)
    final_answer_score = (
        (nlp_evaluation["final_score"] + normalized_score) / 2
        if nlp_evaluation is not None
        else normalized_score
    )
    transcript[-1] = {
        **transcript[-1],
        "evaluation": evaluation,
        "final_score": final_answer_score,
        "ai_provider_status": evaluation_provider_status,
    }
    transcript[-1].pop("evaluation_pending", None)

    answer_record = models.UserAnswer(
        session_id=session.id,
        question_id=bank_question.id if bank_question is not None else None,
        question_text=last_question,
        user_answer=data.answer,
        similarity_score=nlp_evaluation["similarity_score"] if nlp_evaluation else 0.0,
        keyword_score=nlp_evaluation["keyword_score"] if nlp_evaluation else 0.0,
        final_score=final_answer_score,
        missing_concepts=", ".join(str(item) for item in missing_concepts),
        feedback=evaluation.get("feedback", "")
    )
    db.add(answer_record)

    # 3. Synchronize Session Counters
    session.total_questions += 1
    session.average_score = (
        ((session.average_score * (session.total_questions - 1)) + final_answer_score)
        / session.total_questions
    )
    session.transcript = transcript
    session.questions_count = questions_count
    session.score = raw_score

    round_scores = dict(session.round_scores)
    previous_round_score = round_scores.get(session.interview_round, 0.0)
    round_average = (
        (previous_round_score * (questions_count - 1) + raw_score) / questions_count
    )
    round_scores[session.interview_round] = round(round_average, 2)
    session.round_scores = round_scores
    session.score = round_average

    # Determine if question threshold is reached
    should_continue_round = questions_count < round_config["max_questions"]
    if should_continue_round:
        session.transcript = transcript
        db.commit()
        try:
            next_question, next_question_category = await _generate_session_question(
                db, session, company_intel, include_history=True
            )
        except AIProviderTimeout as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Your answer was saved and evaluated, but the next question timed out. Submit again to continue.",
                headers={"Retry-After": "5"},
            ) from error
        session.transcript = [
            *session.transcript,
            {
                "role": "assistant",
                "content": next_question,
                "round": session.interview_round,
                "technical_category": next_question_category,
            },
        ]
        db.commit()
        return {
            "evaluation": evaluation,
            "ai_provider_status": evaluation_provider_status,
            "next_question": next_question,
            "question_category": next_question_category,
            "terminated": False,
            "round_completed": False,
            "overall_status": "in_progress",
            "current_round": session.interview_round,
            "current_round_number": session.current_round_number,
            "questions_asked": questions_count,
            "questions_per_round": round_config["max_questions"],
            "round_score": round(round_average, 1),
            "coding_gate_required": False,
            "behavioral_metrics": behavioral_metrics,
            "total_questions": session.total_questions,
        }

    # Evaluate Round Qualification
    if not should_proceed_to_next_round(round_average, session.interview_round):
        session.overall_status = "failed"
        session.rounds_completed = [
            *session.rounds_completed,
            session.interview_round,
        ]
        completion_message = (
            f"Interview ended because your {session.interview_round} score "
            "did not meet the 6/10 round threshold."
        )
        failed_answer = {
            **transcript[-1],
            "completion": {
                "status": "failed",
                "failed_round": session.interview_round,
                "message": completion_message,
            },
        }
        transcript = [*transcript[:-1], failed_answer]
        session.transcript = transcript
        db.commit()
        await get_memory_service().learn_from_session({
            "target_company": session.target_company,
            "role_category": session.role_category,
            "rounds_completed": session.rounds_completed,
            "score": round_average,
        })
        return {
            "evaluation": evaluation,
            "ai_provider_status": evaluation_provider_status,
            "next_question": None,
            "terminated": True,
            "round_completed": True,
            "round_passed": False,
            "overall_status": "failed",
            "overall_message": completion_message,
            "failed_round": session.interview_round,
            "rounds_completed": session.rounds_completed,
            "round_scores": session.round_scores,
            "round_score": round(round_average, 1),
            "behavioral_metrics": behavioral_metrics,
            "questions_asked": questions_count,
            "total_questions": session.total_questions,
            "questions_per_round": round_config["max_questions"],
            "coding_gate_required": False,
        }

    # Advance to Next Round if available
    next_round = get_next_round(
        session.interview_round,
        session.role_category,
        session.difficulty_level,
        session.job_description,
        company_intel.get("industry") if isinstance(company_intel, dict) else None,
    )
    completed_rounds = [*session.rounds_completed, session.interview_round]
    
    if next_round:
        difficulty_scaled = round_average >= 9.0 and session.difficulty_level < 5
        if difficulty_scaled:
            session.difficulty_level += 1
            session.difficulty = (
                "Beginner" if session.difficulty_level <= 2
                else "Intermediate" if session.difficulty_level == 3
                else "Advanced"
            )
        session.rounds_completed = completed_rounds
        session.current_round_number += 1
        session.interview_round = next_round
        session.questions_count = 0
        transcript[-1]["round_transition"] = {
            "round_completed": True,
            "round_passed": True,
            "next_round": next_round,
            "next_round_number": session.current_round_number,
            "difficulty_scaled": difficulty_scaled,
        }
        session.transcript = transcript
        db.commit()
        try:
            next_q, next_question_category = await _generate_session_question(
                db, session, company_intel, include_history=False
            )
        except AIProviderTimeout as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Your answer was saved and evaluated, but the next-round question timed out. Submit again to continue.",
                headers={"Retry-After": "5"},
            ) from error
        session.transcript = [
            *session.transcript,
            {
                "role": "assistant",
                "content": next_q,
                "round": next_round,
                "technical_category": next_question_category,
            },
        ]
        db.commit()
        return {
            "evaluation": evaluation,
            "ai_provider_status": evaluation_provider_status,
            "next_question": next_q,
            "question_category": next_question_category,
            "terminated": False,
            "round_completed": True,
            "round_passed": True,
            "overall_status": "in_progress",
            "next_round": next_round,
            "next_round_number": session.current_round_number,
            "difficulty_level": session.difficulty_level,
            "difficulty_scaled": difficulty_scaled,
            "rounds_completed": session.rounds_completed,
            "round_scores": session.round_scores,
            "round_score": round(round_average, 1),
            "behavioral_metrics": behavioral_metrics,
            "questions_asked": 0,
            "total_questions": session.total_questions,
            "questions_per_round": _session_questions_per_round(session),
            "coding_gate_required": (
                next_round == "Behavioral/HR"
                and "Technical/Screening" in completed_rounds
            ),
        }

    # All rounds successfully finished
    session.rounds_completed = completed_rounds
    session.overall_status = "completed"
    pending_report_answer = {**transcript[-1], "report_pending": True}
    transcript = [*transcript[:-1], pending_report_answer]
    session.transcript = transcript
    db.commit()
    try:
        master_report_raw = await gemini_service.generate_master_report({
            "transcript": session.transcript,
            "round_scores": session.round_scores,
            "sub_role": session.sub_role,
            "target_company": session.target_company,
            "rounds_completed": session.rounds_completed,
            "required_rounds": list(get_rounds_for_role(
                session.role_category,
                session.job_description,
                company_intel.get("industry") if isinstance(company_intel, dict) else None,
            )),
        })
        master_report = _apply_feedback_tier(
            _validate_hiring_report(_decode_model_json(master_report_raw)),
            current_plan,
        )
        report_provider_status = gemini_service.generation_status()
    except (RuntimeError, HTTPException):
        logger.exception("Could not generate the completed interview report")
        report_provider_status = gemini_service.generation_status()
        pending_report_answer = {
            **transcript[-1],
            "report_provider_status": report_provider_status,
        }
        transcript = [*transcript[:-1], pending_report_answer]
        session.transcript = transcript
        db.commit()
        return {
            "evaluation": evaluation,
            "ai_provider_status": evaluation_provider_status,
            "report_provider_status": report_provider_status,
            "master_report": None,
            "master_report_pending": True,
            "next_question": None,
            "terminated": True,
            "round_completed": True,
            "round_passed": True,
            "interview_completed": True,
            "overall_status": "completed",
            "rounds_completed": session.rounds_completed,
            "round_scores": session.round_scores,
            "round_score": round(round_average, 1),
            "questions_asked": questions_count,
            "total_questions": session.total_questions,
            "questions_per_round": round_config["max_questions"],
            "coding_gate_required": False,
            "behavioral_metrics": behavioral_metrics,
            "overall_message": (
                "All interview rounds are complete. The final scorecard could not "
                "be generated yet; retry the scorecard when ready."
            ),
        }
    completion_message = "Congratulations! You have completed all interview rounds."
    completed_answer = {**transcript[-1]}
    completed_answer.pop("report_pending", None)
    completed_answer["master_report"] = master_report
    completed_answer["report_provider_status"] = report_provider_status
    completed_answer["completion"] = {
        "status": "completed",
        "message": completion_message,
    }
    transcript = [*transcript[:-1], completed_answer]
    session.transcript = transcript
    db.commit()
    await get_memory_service().learn_from_session({
        "target_company": session.target_company,
        "role_category": session.role_category,
        "rounds_completed": session.rounds_completed,
        "score": (
            sum(session.round_scores.values()) / len(session.round_scores)
            if session.round_scores
            else 0
        ),
    })

    return {
        "evaluation": evaluation,
        "ai_provider_status": evaluation_provider_status,
        "report_provider_status": report_provider_status,
        "master_report": master_report,
        "next_question": None,
        "terminated": True,
        "round_completed": True,
        "round_passed": True,
        "interview_completed": True,
        "overall_status": "completed",
        "rounds_completed": session.rounds_completed,
        "round_scores": session.round_scores,
        "round_score": round(round_average, 1),
        "questions_asked": questions_count,
        "total_questions": session.total_questions,
        "questions_per_round": round_config["max_questions"],
        "coding_gate_required": False,
        "behavioral_metrics": behavioral_metrics,
        "overall_message": completion_message,
    }


@app.get("/api/interviews/{session_id}/coding/ledger")
def get_coding_ledger(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _get_owned_interview_session(db, session_id, current_user)
    ledger = db.scalar(
        select(models.CodingRoundLedger).where(
            models.CodingRoundLedger.session_id == session_id,
            models.CodingRoundLedger.user_id == current_user.id,
        )
    )
    if not ledger:
        raise HTTPException(status_code=404, detail="Coding round has not been started.")
    return ledger.ledger_data


@app.post("/api/interviews/{session_id}/coding/problem")
async def start_coding_problem(
    session_id: int,
    payload: schemas.CodingProblemRequest,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    interview_session = _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_number = data["current_round"]
    round_data = data["rounds"][str(round_number)]
    if round_data["problem"]:
        db.commit()
        return data
    if round_data["status"] != "active":
        raise HTTPException(
            status_code=409,
            detail="Use the round progression or reattempt action to continue.",
        )

    problem = await _generate_coding_problem(
        interview_session, round_number, payload.language
    )
    round_data["problem"] = problem
    round_data["language"] = payload.language
    ledger.ledger_data = data
    db.commit()
    return data


@app.post("/api/interviews/{session_id}/coding/hint")
async def get_coding_hint(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    interview_session = _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_number = data["current_round"]
    round_data = data["rounds"][str(round_number)]
    if round_data["status"] != "active" or not round_data["problem"]:
        raise HTTPException(status_code=409, detail="There is no active coding problem.")
    tier = len(round_data["hints"]) + 1
    if tier > 5:
        raise HTTPException(status_code=409, detail="All five hint tiers have been used.")
    last_attempt = round_data["attempts"][-1] if round_data["attempts"] else {}
    raw = await gemini_service.generate_coding_hint(
        problem=round_data["problem"],
        code=last_attempt.get("code", ""),
        explanation=last_attempt.get("explanation", ""),
        tier=tier,
        interviewer_name=interview_session.interviewer_name,
    )
    hint = validate_hint(_decode_model_json(raw), tier)
    round_data["hints"].append(hint)
    ledger.ledger_data = data
    db.commit()
    return hint


@app.post("/api/interviews/{session_id}/coding/submit")
async def submit_coding_solution(
    session_id: int,
    payload: schemas.CodingSubmission,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    interview_session = _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_number = data["current_round"]
    round_data = data["rounds"][str(round_number)]
    if round_data["status"] != "active" or not round_data["problem"]:
        raise HTTPException(status_code=409, detail="There is no active coding problem.")
    if (
        interview_session.interviewer_name.strip().casefold() == "veda"
        and len(payload.explanation.split()) < 12
    ):
        raise HTTPException(
            status_code=422,
            detail="Veda's verbalization gate requires an approach explanation of at least 12 words.",
        )

    raw = await gemini_service.judge_coding_solution(
        problem=round_data["problem"],
        code=payload.code,
        explanation=payload.explanation,
        role=interview_session.role_category,
        sub_role=interview_session.sub_role,
        difficulty=interview_session.difficulty_level,
        company=interview_session.target_company,
        interviewer_name=interview_session.interviewer_name,
    )
    evaluation = normalize_judgement(
        _decode_model_json(raw),
        interview_session.role_category,
        interview_session.sub_role,
    )
    attempt = {
        "submitted_at": datetime.now(timezone.utc).isoformat(),
        "code": payload.code,
        "explanation": payload.explanation,
        "hints_used": len(round_data["hints"]),
        "evaluation": evaluation,
    }
    round_data["attempts"].append(attempt)
    round_data["latest_evaluation"] = evaluation
    round_data["latest_score"] = evaluation["total_score"]
    round_data["status"] = "passed" if evaluation["passed"] else "failed"
    if evaluation["passed"] and round_number == 2:
        data["status"] = "completed"
    ledger.ledger_data = data
    db.commit()
    return {
        "evaluation": evaluation,
        "ledger": data,
        "roadmap_available": not evaluation["passed"],
    }


@app.post("/api/interviews/{session_id}/coding/roadmap")
async def generate_coding_roadmap(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    interview_session = _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_number = data["current_round"]
    round_data = data["rounds"][str(round_number)]
    if round_data["status"] != "failed":
        raise HTTPException(status_code=409, detail="A learning roadmap is available after a failed attempt.")
    if round_data["roadmap"]:
        return round_data["roadmap"]
    raw = await gemini_service.generate_coding_learning_roadmap(
        role=interview_session.role_category,
        sub_role=interview_session.sub_role,
        problem=round_data["problem"],
        attempts=round_data["attempts"],
    )
    roadmap = validate_roadmap(_decode_model_json(raw))
    round_data["roadmap"] = roadmap
    ledger.ledger_data = data
    db.commit()
    return roadmap


@app.post("/api/interviews/{session_id}/coding/roadmap/complete")
def complete_coding_roadmap(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_data = data["rounds"][str(data["current_round"])]
    if round_data["status"] != "failed" or not round_data["roadmap"]:
        raise HTTPException(status_code=409, detail="Generate and complete the learning roadmap first.")
    round_data["roadmap_completed"] = True
    ledger.ledger_data = data
    db.commit()
    return {"roadmap_completed": True}


@app.post("/api/interviews/{session_id}/coding/retry")
def retry_coding_problem(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    round_data = data["rounds"][str(data["current_round"])]
    if round_data["status"] != "failed" or not round_data["roadmap_completed"]:
        raise HTTPException(status_code=409, detail="Complete the learning roadmap before reattempting.")
    round_data["status"] = "active"
    round_data["hints"] = []
    round_data["latest_evaluation"] = None
    round_data["latest_score"] = None
    round_data["roadmap_completed"] = False
    ledger.ledger_data = data
    db.commit()
    return data


@app.post("/api/interviews/{session_id}/coding/next")
async def advance_coding_round(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    interview_session = _get_owned_interview_session(db, session_id, current_user)
    ledger = _get_or_create_coding_ledger(db, session_id, current_user.id)
    data = deepcopy(ledger.ledger_data)
    if data["current_round"] != 1 or data["rounds"]["1"]["status"] != "passed":
        raise HTTPException(
            status_code=403,
            detail="Round 1 must score above 70% before Round 2 unlocks.",
        )
    language = data["rounds"]["1"].get("language", "python")
    problem = await _generate_coding_problem(interview_session, 2, language)
    data["current_round"] = 2
    data["unlocked_rounds"] = [1, 2]
    data["rounds"]["2"] = {
        "status": "active",
        "problem": problem,
        "language": language,
        "hints": [],
        "attempts": [],
        "latest_evaluation": None,
        "latest_score": None,
        "roadmap": None,
        "roadmap_completed": False,
    }
    ledger.ledger_data = data
    db.commit()
    return data


# ==========================================
# MODULE 6, 7 & 8: HISTORY & ANALYTICS
# ==========================================

@app.get("/api/interviews/history")
async def get_interview_history(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    sessions = db.scalars(
        select(models.InterviewSession)
        .where(models.InterviewSession.user_id == current_user.id)
        .order_by(models.InterviewSession.created_at.desc())
    ).all()
    
    return [
        {
            "session_id": s.id,
            "role": s.role_category,
            "sub_role": s.sub_role,
            "difficulty": s.difficulty,
            "category": s.category,
            "total_questions": s.total_questions,
            "average_score": round(s.average_score, 1),
            "status": s.overall_status,
            "target_company": s.target_company,
            "round_scores": s.round_scores or {},
            "rounds_completed": s.rounds_completed or [],
            "current_round": s.interview_round,
            "questions_asked": s.questions_count,
            "questions_per_round": _session_questions_per_round(s),
            "created_at": s.created_at.isoformat()
        }
        for s in sessions
    ]


@app.get("/api/interviews/history/{session_id}")
def get_interview_history_detail(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == session_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    answers = db.scalars(
        select(models.UserAnswer)
        .where(models.UserAnswer.session_id == session.id)
        .order_by(models.UserAnswer.created_at, models.UserAnswer.id)
    ).all()
    coding_ledger = db.scalar(
        select(models.CodingRoundLedger).where(
            models.CodingRoundLedger.session_id == session.id,
            models.CodingRoundLedger.user_id == current_user.id,
        )
    )
    coding_gate_required = (
        session.interview_round == "Behavioral/HR"
        and "Technical/Screening" in session.rounds_completed
        and (not coding_ledger or coding_ledger.ledger_data.get("status") != "completed")
    )
    return {
        "session_id": session.id,
        "role": session.role_category,
        "sub_role": session.sub_role,
        "difficulty": session.difficulty,
        "difficulty_level": session.difficulty_level,
        "target_company": session.target_company,
        "interviewer_name": session.interviewer_name,
        "is_panel": session.is_panel,
        "interview_round": session.interview_round,
        "questions_asked": session.questions_count,
        "questions_per_round": _session_questions_per_round(session),
        "coding_gate_required": coding_gate_required,
        "category": session.category,
        "status": session.overall_status,
        "rounds_completed": session.rounds_completed,
        "round_scores": session.round_scores,
        "average_score": round(session.average_score, 1),
        "total_questions": len(answers),
        "transcript": session.transcript,
        "created_at": session.created_at.isoformat(),
        "answers": [
            {
                "answer_id": answer.id,
                "question_id": answer.question_id,
                "question": answer.question_text,
                "answer": answer.user_answer,
                "reference_answer": (
                    answer.question.reference_answer if answer.question else None
                ),
                "similarity_score": answer.similarity_score,
                "keyword_score": answer.keyword_score,
                "final_score": answer.final_score,
                "missing_concepts": [
                    item.strip()
                    for item in answer.missing_concepts.split(",")
                    if item.strip()
                ],
                "feedback": answer.feedback,
                "created_at": answer.created_at.isoformat(),
            }
            for answer in answers
        ],
    }


@app.post("/api/interviews/history/{session_id}/answers/{answer_id}/retry")
async def retry_interview_answer(
    session_id: int,
    answer_id: int,
    data: schemas.AnswerRetry,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = _get_owned_interview_session(db, session_id, current_user)
    original_answer = db.scalar(
        select(models.UserAnswer).where(
            models.UserAnswer.id == answer_id,
            models.UserAnswer.session_id == session.id,
        )
    )
    if original_answer is None:
        raise HTTPException(status_code=404, detail="Interview answer not found.")

    transcript = session.transcript if isinstance(session.transcript, list) else []
    question_round = next(
        (
            item.get("round")
            for item in reversed(transcript)
            if item.get("role") == "assistant"
            and item.get("content") == original_answer.question_text
            and item.get("round")
        ),
        session.interview_round,
    )
    round_config = get_round_config(question_round)
    company_intel = await _get_company_intelligence(
        session.target_company,
        session.job_description,
        _session_target_geography(session),
    )
    evaluation = _decode_model_json(
        await gemini_service.evaluate_answer(
            question=original_answer.question_text,
            answer=data.answer,
            role=session.role_category,
            round_name=question_round,
            company=session.target_company,
            company_intel=company_intel,
            round_criteria=round_config["evaluation_criteria"],
        )
    )
    if get_user_plan(db, current_user.id) == "elite":
        evaluation["vibe_assessment"] = _validate_vibe_assessment(
            evaluation.get("vibe_assessment")
        )
    else:
        evaluation.pop("vibe_assessment", None)
    raw_score = evaluation.get("score")
    if isinstance(raw_score, bool):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation did not include a valid numeric score.",
        )
    try:
        numeric_score = float(raw_score)
    except (TypeError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation did not include a valid numeric score.",
        ) from error
    if not math.isfinite(numeric_score) or not 0 <= numeric_score <= 10:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI evaluation score must be between 0 and 10.",
        )

    score = numeric_score * 10
    missing_concepts = evaluation.get("improvements", [])
    if not isinstance(missing_concepts, list):
        missing_concepts = [str(missing_concepts)]
    retry_answer = models.UserAnswer(
        session_id=session.id,
        question_id=original_answer.question_id,
        question_text=original_answer.question_text,
        user_answer=data.answer,
        similarity_score=0.0,
        keyword_score=0.0,
        final_score=score,
        missing_concepts=", ".join(str(item) for item in missing_concepts),
        feedback=evaluation.get("feedback", ""),
    )
    db.add(retry_answer)
    db.commit()
    db.refresh(retry_answer)
    return {
        "answer_id": retry_answer.id,
        "question": retry_answer.question_text,
        "answer": retry_answer.user_answer,
        "final_score": retry_answer.final_score,
        "feedback": retry_answer.feedback,
        "missing_concepts": missing_concepts,
        "evaluation": evaluation,
    }


@app.post("/api/interviews/history/{session_id}/learning-roadmap")
async def generate_interview_learning_roadmap(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == session_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    _require_plan(db, current_user, "elite")
    saved_roadmap = next(
        (
            item.get("roadmap")
            for item in reversed(session.transcript or [])
            if item.get("role") == "learning_roadmap" and isinstance(item.get("roadmap"), dict)
        ),
        None,
    )
    if saved_roadmap:
        return {"session_id": session.id, **saved_roadmap}

    answers = db.scalars(
        select(models.UserAnswer)
        .where(models.UserAnswer.session_id == session.id)
        .order_by(models.UserAnswer.created_at, models.UserAnswer.id)
    ).all()
    if not answers:
        raise HTTPException(
            status_code=409,
            detail="Answer at least one interview question before requesting a roadmap.",
        )

    session_data = {
        "role": session.role_category,
        "sub_role": session.sub_role,
        "target_company": session.target_company,
        "round_scores": session.round_scores,
        "answers": [
            {
                "question": answer.question_text,
                "answer": answer.user_answer,
                "score": answer.final_score,
                "missing_topics": [
                    item.strip()
                    for item in answer.missing_concepts.split(",")
                    if item.strip()
                ],
                "feedback": answer.feedback,
            }
            for answer in answers
        ],
    }
    roadmap = _decode_model_json(
        await gemini_service.generate_learning_roadmap(session_data)
    )
    days = roadmap.get("days")
    if (
        not isinstance(days, list)
        or len(days) != 7
        or any(
            not isinstance(day, dict)
            or day.get("day") != index
            or not isinstance(day.get("focus"), str)
            or not isinstance(day.get("activities"), list)
            or not isinstance(day.get("practice_prompt"), str)
            for index, day in enumerate(days, start=1)
        )
        or not isinstance(roadmap.get("failed_topics"), list)
        or not isinstance(roadmap.get("resource_recommendations"), list)
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI service returned an invalid 7-day learning roadmap.",
        )
    session.transcript = [
        *(session.transcript or []),
        {
            "role": "learning_roadmap",
            "roadmap": roadmap,
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    ]
    db.commit()
    return {"session_id": session.id, **roadmap}


@app.get("/api/interviews/history/{session_id}/learning-roadmap")
def get_interview_learning_roadmap(
    session_id: int,
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    session = db.scalar(
        select(models.InterviewSession).where(
            models.InterviewSession.id == session_id,
            models.InterviewSession.user_id == current_user.id,
        )
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Interview session not found.")
    _require_plan(db, current_user, "elite")
    roadmap = next(
        (
            item.get("roadmap")
            for item in reversed(session.transcript or [])
            if item.get("role") == "learning_roadmap" and isinstance(item.get("roadmap"), dict)
        ),
        None,
    )
    if roadmap is None:
        raise HTTPException(status_code=404, detail="No learning roadmap has been saved for this interview.")
    return {"session_id": session.id, **roadmap}


@app.get("/api/interviews/analytics", response_model=schemas.PerformanceAnalytics)
def get_user_analytics(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    sessions = db.scalars(
        select(models.InterviewSession).where(models.InterviewSession.user_id == current_user.id)
    ).all()

    if not sessions:
        return schemas.PerformanceAnalytics(
            total_interviews=0,
            total_questions_attempted=0,
            overall_average_score=0.0,
            weakest_areas=[],
            recommendations=[]
        )

    session_ids = [s.id for s in sessions]
    answers = db.scalars(
        select(models.UserAnswer).where(models.UserAnswer.session_id.in_(session_ids))
    ).all()

    missing_concept_freq: dict[str, int] = {}
    strength_freq: dict[str, int] = {}
    for a in answers:
        missing_items = {
            item.strip().casefold()
            for item in a.missing_concepts.split(",")
            if item.strip()
        }
        if a.final_score < 70.0 and a.missing_concepts:
            for item in missing_items:
                missing_concept_freq[item] = missing_concept_freq.get(item, 0) + 1
        if a.final_score >= 80.0 and a.question is not None:
            for concept in a.question.key_concepts.split(","):
                concept = concept.strip()
                if concept and concept.casefold() not in missing_items:
                    strength_freq[concept] = strength_freq.get(concept, 0) + 1

    weakest = sorted(missing_concept_freq, key=missing_concept_freq.get, reverse=True)[:5]
    strengths = sorted(strength_freq, key=strength_freq.get, reverse=True)[:5]

    recommendations = []
    for concept in weakest:
        related_q = db.scalars(
            select(models.Question.question_text)
            .where(models.Question.key_concepts.ilike(f"%{concept}%"))
            .limit(2)
        ).all()
        recommendations.append(
            schemas.RecommendationOut(
                topic=concept,
                advice=f"Focus on core principles and practice architectural questions covering '{concept}'.",
                recommended_questions=list(related_q)
            )
        )

    scored_sessions = [
        session
        for session in sessions
        if session.overall_status in {"completed", "failed"}
    ]
    overall_avg = (
        sum(session.average_score for session in scored_sessions) / len(scored_sessions)
        if scored_sessions
        else 0.0
    )
    trend = [
        schemas.ScoreTrendOut(
            session_id=session.id,
            date=session.created_at,
            role=session.role_category,
            score=round(session.average_score, 1),
        )
        for session in sorted(scored_sessions, key=lambda item: item.created_at)
    ]

    round_totals: dict[str, list[float]] = {}
    behavioral_rates: list[float] = []
    speaking_paces: list[float] = []
    vibe_scores: dict[str, list[float]] = {}
    for session in sessions:
        for round_name, score in (session.round_scores or {}).items():
            round_totals.setdefault(round_name, []).append(float(score) * 10)
        for item in session.transcript or []:
            if not isinstance(item, dict):
                continue
            metrics = item.get("behavioral_metrics")
            if isinstance(metrics, dict):
                filler_rate = metrics.get("filler_rate_per_100_words")
                if isinstance(filler_rate, (int, float)) and math.isfinite(filler_rate):
                    behavioral_rates.append(float(filler_rate))
                pace = metrics.get("words_per_minute")
                if isinstance(pace, (int, float)) and math.isfinite(pace):
                    speaking_paces.append(float(pace))
            evaluation = item.get("evaluation")
            vibe = (
                evaluation.get("vibe_assessment")
                if isinstance(evaluation, dict)
                else None
            )
            if isinstance(vibe, dict):
                for category, assessment in vibe.items():
                    if (
                        isinstance(assessment, dict)
                        and isinstance(assessment.get("score"), (int, float))
                        and math.isfinite(assessment["score"])
                    ):
                        vibe_scores.setdefault(category, []).append(
                            float(assessment["score"])
                        )

    return schemas.PerformanceAnalytics(
        total_interviews=len(sessions),
        total_questions_attempted=len(answers),
        overall_average_score=round(overall_avg, 1),
        weakest_areas=weakest,
        recommendations=recommendations,
        completed_interviews=sum(
            session.overall_status == "completed" for session in sessions
        ),
        score_trend=trend,
        round_averages={
            name: round(sum(scores) / len(scores), 1)
            for name, scores in round_totals.items()
        },
        strengths=strengths,
        average_filler_rate_per_100_words=(
            round(sum(behavioral_rates) / len(behavioral_rates), 1)
            if behavioral_rates
            else None
        ),
        average_speaking_pace_wpm=(
            round(sum(speaking_paces) / len(speaking_paces), 1)
            if speaking_paces
            else None
        ),
        vibe_averages={
            category: round(sum(scores) / len(scores), 1)
            for category, scores in vibe_scores.items()
        },
    )


@app.get("/api/interviews/analytics/chart")
def get_analytics_chart(
    db: Session = Depends(database.get_db),
    current_user: models.User = Depends(auth_utils.get_current_user)
):
    sessions = db.scalars(
        select(models.InterviewSession)
        .where(models.InterviewSession.user_id == current_user.id)
        .order_by(models.InterviewSession.created_at.asc())
    ).all()
    sessions = [
        session
        for session in sessions
        if session.overall_status in {"completed", "failed"}
    ]

    if not sessions:
        raise HTTPException(status_code=400, detail="No interview history found to plot.")

    scores = [s.average_score for s in sessions]
    dates = [s.created_at.strftime("%b %d %H:%M") for s in sessions]

    img_png = generate_performance_chart(scores, dates)
    return Response(content=img_png, media_type="image/png")


# ==========================================
# RESUME PARSER
# ==========================================

@app.post("/api/resume/parse")
async def upload_and_parse_resume(
    file: UploadFile = File(...),
    current_user: models.User = Depends(auth_utils.get_current_user),
):
    del current_user
    if not file.filename or Path(file.filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Resume must be a PDF file.")
    file_content = await file.read(MAX_RESUME_SIZE_BYTES + 1)
    if len(file_content) > MAX_RESUME_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Resume exceeds the 10 MB limit.")
    if not file_content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid PDF.")
    try:
        detected_skills = await run_in_threadpool(
            parse_resume_skills_from_bytes, file_content
        )
    except Exception as error:
        raise HTTPException(status_code=400, detail="Could not read the uploaded PDF.") from error
    return {
        "filename": Path(file.filename).name,
        "detected_skills": detected_skills,
        "message": f"Resume analyzed successfully! Found {len(detected_skills)} matching core skills."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app",
        host="127.0.0.1",
        port=8001,
        reload=True,
        reload_dirs=[str(Path(__file__).resolve().parent)],
        reload_excludes=["**/venv/**", "**/.venv/**"],
    )