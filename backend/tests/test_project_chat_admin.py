import json
import os
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

os.environ.setdefault(
    "MYSQL_URL",
    "mysql+pymysql://user:password@127.0.0.1:3306/interviewai_test?charset=utf8mb4",
)
os.environ["JWT_SECRET_KEY"] = "backend-tests-only-secret-0123456789"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, text
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app as backend_app
from core import database
from core.models import (
    CandidateProfile,
    CodingRoundLedger,
    DevelopmentWorkflow,
    InterviewSession,
    PaymentSubmission,
    PlanUsage,
    ResumeDocument,
    Subscription,
    User,
    UserAccessControl,
    UserAnswer,
)


@compiles(MEDIUMBLOB, "sqlite")
def compile_mediumblob_for_sqlite(_type, _compiler, **_kwargs):
    return "BLOB"


class ProjectChatAdminTests(unittest.TestCase):
    def setUp(self):
        self.original_engine = database.engine
        self.original_session_factory = database.SessionLocal
        self.original_super_admin_emails = os.environ.get("SUPER_ADMIN_EMAILS")
        os.environ["SUPER_ADMIN_EMAILS"] = "admin@example.com"
        self.test_engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database.engine = self.test_engine
        database.SessionLocal = sessionmaker(
            bind=self.test_engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.client_context = TestClient(backend_app.app)
        self.client = self.client_context.__enter__()
        self.admin_headers = self._register("admin@example.com")
        self.user_headers = self._register(f"user-{uuid4().hex}@example.com")

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        database.engine = self.original_engine
        database.SessionLocal = self.original_session_factory
        self.test_engine.dispose()
        if self.original_super_admin_emails is None:
            os.environ.pop("SUPER_ADMIN_EMAILS", None)
        else:
            os.environ["SUPER_ADMIN_EMAILS"] = self.original_super_admin_emails

    def _register(self, email):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "Test Account",
                "email": email,
                "password": "secure-password-123",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_history_server_errors_keep_cors_headers(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        origin = "https://ai-interview-prep-swart-mu.vercel.app"
        with (
            patch.object(
                backend_app,
                "_session_selection_result",
                side_effect=ValueError("test failure"),
            ),
            TestClient(backend_app.app, raise_server_exceptions=False) as client,
        ):
            response = client.get(
                f"/api/interviews/history/{interview_id}",
                headers={**self.user_headers, "Origin": origin},
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            origin,
        )

    def test_invalid_learning_roadmap_is_repaired_once(self):
        now = datetime.now(timezone.utc)
        valid_roadmap = {
            "days": [
                {
                    "day": day,
                    "focus": f"Focus {day}",
                    "activities": [f"Practice {day}"],
                    "practice_prompt": f"Prompt {day}",
                }
                for day in range(1, 8)
            ],
            "failed_topics": ["API design"],
            "resource_recommendations": ["REST API documentation"],
        }
        invalid_response = json.dumps({"days": []})
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
            )
            db.add(session)
            db.flush()
            db.add_all(
                [
                    Subscription(
                        user_id=user.id,
                        plan="elite",
                        status="active",
                        started_at=now,
                        expires_at=now + timedelta(days=30),
                    ),
                    UserAnswer(
                        session_id=session.id,
                        question_text="How would you design a scalable API?",
                        user_answer="I would add pagination and caching.",
                        final_score=6,
                    ),
                ]
            )
            interview_id = session.id
            db.commit()

        with (
            patch.object(
                backend_app.gemini_service,
                "generate_learning_roadmap",
                new_callable=AsyncMock,
                return_value=invalid_response,
            ),
            patch.object(
                backend_app.gemini_service,
                "repair_learning_roadmap",
                new_callable=AsyncMock,
                return_value=json.dumps(valid_roadmap),
            ) as repair,
        ):
            response = self.client.post(
                f"/api/interviews/history/{interview_id}/learning-roadmap",
                headers=self.user_headers,
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(response.json()["days"]), 7)
        self.assertEqual(response.json()["days"][0]["day"], 1)
        self.assertEqual(repair.await_count, 1)
        self.assertEqual(
            repair.await_args.kwargs["validation_errors"],
            ["days"],
        )

    def test_round_preview_uses_the_authenticated_candidate_profile(self):
        response = self.client.get(
            "/api/interviews/rounds",
            params={"role": "Software Engineer"},
            headers=self.user_headers,
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()[0]["candidate_level"], "general")
        self.assertEqual(len(response.json()), 5)

        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            profile = CandidateProfile(
                user_id=user.id,
                employment_status="college_student",
                years_of_experience=1.5,
            )
            db.add(profile)
            db.commit()

        fresher_response = self.client.get(
            "/api/interviews/rounds",
            params={"role": "Software Engineer"},
            headers=self.user_headers,
        )
        self.assertEqual(fresher_response.status_code, 200, fresher_response.text)
        self.assertEqual(fresher_response.json()[0]["candidate_level"], "fresher")
        self.assertEqual(
            [round_info["name"] for round_info in fresher_response.json()],
            ["Technical/Screening", "Behavioral/HR", "System Design"],
        )

        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            profile = db.get(CandidateProfile, user.id)
            profile.employment_status = "employed"
            profile.years_of_experience = 5
            db.commit()

        experienced_response = self.client.get(
            "/api/interviews/rounds",
            params={"role": "Software Engineer"},
            headers=self.user_headers,
        )
        self.assertEqual(experienced_response.status_code, 200, experienced_response.text)
        self.assertEqual(experienced_response.json()[0]["candidate_level"], "experienced")
        self.assertEqual(len(experienced_response.json()), 5)

    def test_session_round_plan_is_stable_after_candidate_profile_changes(self):
        planned_rounds = [
            "Technical/Screening",
            "Behavioral/HR",
            "System Design",
        ]
        session = InterviewSession(
            user_id=1,
            role_category="Software Engineer",
            sub_role="Backend",
            transcript=[
                {
                    "role": "system",
                    "candidate_level": "fresher",
                    "planned_rounds": planned_rounds,
                }
            ],
        )

        self.assertEqual(backend_app._session_round_plan(session), planned_rounds)

    def _add_interview_session(self, created_at):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                InterviewSession(
                    user_id=user.id,
                    role_category="Software Engineer",
                    sub_role="Backend",
                    created_at=created_at,
                )
            )
            db.commit()

    def _start_basic_interview(self):
        with (
            patch.object(
                backend_app,
                "_get_company_intelligence",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_interview_question",
                new_callable=AsyncMock,
                return_value="How would you design this system?",
            ),
        ):
            return self.client.post(
                "/interviews/start",
                headers=self.user_headers,
                json={
                    "role_category": "Software Engineer",
                    "sub_role": "Backend",
                },
            )

    def test_free_interview_limit_blocks_fourth_start_in_month(self):
        now = datetime.now(timezone.utc)
        for offset in range(3):
            self._add_interview_session(now - timedelta(minutes=offset + 1))

        response = self.client.post(
            "/interviews/start",
            headers=self.user_headers,
            json={
                "role_category": "Software Engineer",
                "sub_role": "Backend",
            },
        )

        self.assertEqual(response.status_code, 429, response.text)
        self.assertEqual(
            response.json()["detail"],
            "The Free plan allows 3 mock interviews per month.",
        )

    def test_free_interview_limit_allows_third_start_in_month(self):
        self._add_interview_session(
            datetime.now(timezone.utc) - timedelta(hours=2, seconds=1)
        )

        response = self._start_basic_interview()

        self.assertEqual(response.status_code, 200, response.text)

    def test_paid_plan_bypasses_free_interview_limit(self):
        now = datetime.now(timezone.utc)
        self._add_interview_session(now - timedelta(minutes=30))
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pro",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.commit()

        response = self._start_basic_interview()

        self.assertEqual(response.status_code, 200, response.text)

    def test_pro_interview_limit_blocks_twenty_first_start_in_month(self):
        now = datetime.now(timezone.utc)
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pro",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.commit()
        for offset in range(20):
            self._add_interview_session(now - timedelta(minutes=offset + 1))

        response = self.client.post(
            "/interviews/start",
            headers=self.user_headers,
            json={
                "role_category": "Software Engineer",
                "sub_role": "Backend",
            },
        )

        self.assertEqual(response.status_code, 429, response.text)
        self.assertEqual(
            response.json()["detail"],
            "The Pro plan allows 20 mock interviews per month.",
        )

    def test_elite_interview_limit_is_unlimited(self):
        now = datetime.now(timezone.utc)
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="elite",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.commit()
        for offset in range(25):
            self._add_interview_session(now - timedelta(minutes=offset + 1))

        response = self._start_basic_interview()

        self.assertEqual(response.status_code, 200, response.text)

    def test_subscription_response_reports_interview_limit_by_plan(self):
        free_response = self.client.get(
            "/api/billing/subscription",
            headers=self.user_headers,
        )
        self.assertEqual(free_response.status_code, 200, free_response.text)
        self.assertEqual(
            free_response.json()["interview_limit"],
            "3 per month",
        )
        self.assertEqual(free_response.json()["resume_analysis_limit"], "1 per month")
        self.assertEqual(free_response.json()["company_question_limit"], "not included")

        now = datetime.now(timezone.utc)
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pre",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.commit()

        paid_response = self.client.get(
            "/api/billing/subscription",
            headers=self.user_headers,
        )
        self.assertEqual(paid_response.status_code, 200, paid_response.text)
        self.assertEqual(paid_response.json()["interview_limit"], "unlimited")
        self.assertEqual(paid_response.json()["plan"], "legacy_resume")

    def test_free_feedback_hides_detailed_evidence(self):
        basic_report = {
            "overall_score": 8,
            "final_verdict": "LEAN HIRE",
            "strengths": ["Clear reasoning"],
            "areas_to_improve": ["Add measurable outcomes"],
            "recruiter_closing_note": "Keep practicing.",
        }

        result = backend_app._apply_feedback_tier(basic_report, "free")

        self.assertNotIn("strengths", result)
        self.assertNotIn("areas_to_improve", result)
        self.assertEqual(result["overall_score"], 8)

    def test_free_user_can_run_multiple_ats_analyses_without_quota_usage(self):
        with patch.object(
            backend_app,
            "calculate_detailed_ats_score",
            return_value={"ats_score": 76},
        ) as analyze, patch.object(
            backend_app.gemini_service,
            "predict_resume_match",
            new=AsyncMock(return_value={"match_score": 70}),
        ) as predict:
            first = self.client.post(
                "/api/ats/analyze",
                headers=self.user_headers,
                data={
                    "resume_text": "Python engineer",
                    "target_role": "Engineer",
                    "ai_processing_acknowledged": "true",
                },
            )
            second = self.client.post(
                "/api/ats/analyze",
                headers=self.user_headers,
                data={
                    "resume_text": "Python engineer",
                    "target_role": "Engineer",
                    "ai_processing_acknowledged": "true",
                },
            )
            third = self.client.post(
                "/api/ats/analyze",
                headers=self.user_headers,
                data={
                    "resume_text": "Python engineer",
                    "target_role": "Engineer",
                    "ai_processing_acknowledged": "true",
                },
            )

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(first.json()["ai_match_prediction"]["match_score"], 70)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(third.status_code, 200, third.text)
        self.assertEqual(analyze.call_count, 3)
        self.assertEqual(predict.await_count, 3)
        subscription = self.client.get(
            "/api/billing/subscription",
            headers=self.user_headers,
        )
        self.assertEqual(subscription.status_code, 200, subscription.text)
        self.assertEqual(subscription.json()["resume_analyses_remaining"], 1)

    def test_ats_target_job_description_uses_pasted_resume(self):
        generated = {
            "target_role": "Backend Python Engineer",
            "job_description": "Python API and database experience.",
        }
        with patch.object(
            backend_app.gemini_service,
            "generate_target_job_description",
            new=AsyncMock(return_value=generated),
        ) as generate:
            response = self.client.post(
                "/api/ats/generate-target",
                headers=self.user_headers,
                data={
                    "resume_text": "Built Python APIs and PostgreSQL services.",
                    "ai_processing_acknowledged": "true",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), generated)
        generate.assert_awaited_once_with(
            "Built Python APIs and PostgreSQL services."
        )

    def test_ats_target_job_description_extracts_uploaded_pdf(self):
        generated = {
            "target_role": "Backend Python Engineer",
            "job_description": "Python API and database experience.",
        }
        with (
            patch.object(
                backend_app,
                "_extract_resume_text",
                return_value="Built Python APIs and PostgreSQL services.",
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_target_job_description",
                new=AsyncMock(return_value=generated),
            ) as generate,
        ):
            response = self.client.post(
                "/api/ats/generate-target",
                headers=self.user_headers,
                data={"ai_processing_acknowledged": "true"},
                files={"file": ("resume.pdf", b"%PDF-test", "application/pdf")},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), generated)
        generate.assert_awaited_once_with(
            "Built Python APIs and PostgreSQL services."
        )

    def test_ats_target_job_description_requires_ai_processing_acknowledgment(self):
        with patch.object(
            backend_app.gemini_service,
            "generate_target_job_description",
            new=AsyncMock(),
        ) as generate:
            response = self.client.post(
                "/api/ats/generate-target",
                headers=self.user_headers,
                data={"resume_text": "Python engineer"},
            )

        self.assertEqual(response.status_code, 400, response.text)
        generate.assert_not_awaited()

    def test_resume_analysis_requires_ai_processing_acknowledgment(self):
        with patch.object(
            backend_app.gemini_service,
            "predict_resume_match",
            new=AsyncMock(),
        ) as predict:
            response = self.client.post(
                "/api/ats/analyze",
                headers=self.user_headers,
                data={
                    "resume_text": "Python engineer",
                    "target_role": "Engineer",
                },
            )

        self.assertEqual(response.status_code, 400, response.text)
        predict.assert_not_awaited()

    def test_pro_user_can_run_ats_analysis_after_other_resume_quota_is_used(self):
        now = datetime.now(timezone.utc)
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pro",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.add_all(
                PlanUsage(user_id=user.id, usage_type="resume_analysis")
                for _ in range(5)
            )
            db.commit()

        with patch.object(
            backend_app,
            "calculate_detailed_ats_score",
            return_value={"ats_score": 76},
        ) as analyze, patch.object(
            backend_app.gemini_service,
            "predict_resume_match",
            new=AsyncMock(return_value={"match_score": 70}),
        ) as predict:
            response = self.client.post(
                "/api/ats/analyze",
                headers=self.user_headers,
                data={
                    "resume_text": "Python engineer",
                    "target_role": "Engineer",
                    "ai_processing_acknowledged": "true",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        analyze.assert_called_once()
        predict.assert_awaited_once()

    def test_free_plan_cannot_start_company_specific_interview(self):
        response = self.client.post(
            "/interviews/start",
            headers=self.user_headers,
            json={
                "role_category": "Software Engineer",
                "sub_role": "Backend",
                "target_company": "Google",
            },
        )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertIn("requires the Pro plan", response.json()["detail"])

    def test_pro_company_question_quota_is_thirty_per_month(self):
        now = datetime.now(timezone.utc)
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                Subscription(
                    user_id=user.id,
                    plan="pro",
                    status="active",
                    started_at=now,
                    expires_at=now + timedelta(days=30),
                )
            )
            db.add_all(
                PlanUsage(user_id=user.id, usage_type="company_question")
                for _ in range(30)
            )
            db.commit()

        with patch.object(
            backend_app,
            "_get_company_intelligence",
            new_callable=AsyncMock,
            return_value={"industry": "Technology"},
        ):
            response = self.client.post(
                "/interviews/start",
                headers=self.user_headers,
                json={
                    "role_category": "Software Engineer",
                    "sub_role": "Backend",
                    "target_company": "Google",
                },
            )

        self.assertEqual(response.status_code, 429, response.text)
        self.assertIn("all 30 company-specific questions", response.json()["detail"])

    def test_password_change_requires_current_password_and_updates_login(self):
        wrong_password = self.client.post(
            "/api/users/me/password",
            headers=self.user_headers,
            json={
                "current_password": "incorrect-password",
                "new_password": "new-secure-password-456",
            },
        )
        self.assertEqual(wrong_password.status_code, 400, wrong_password.text)

        same_password = self.client.post(
            "/api/users/me/password",
            headers=self.user_headers,
            json={
                "current_password": "secure-password-123",
                "new_password": "secure-password-123",
            },
        )
        self.assertEqual(same_password.status_code, 400, same_password.text)

        changed = self.client.post(
            "/api/users/me/password",
            headers=self.user_headers,
            json={
                "current_password": "secure-password-123",
                "new_password": "new-secure-password-456",
            },
        )
        self.assertEqual(changed.status_code, 200, changed.text)
        self.assertEqual(changed.json()["message"], "Password changed successfully.")

        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            email = user.email
        old_login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "secure-password-123"},
        )
        self.assertEqual(old_login.status_code, 401)
        new_login = self.client.post(
            "/api/auth/login",
            json={"email": email, "password": "new-secure-password-456"},
        )
        self.assertEqual(new_login.status_code, 200, new_login.text)

    def test_chat_requires_authentication_and_uses_project_service(self):
        unauthorized = self.client.post(
            "/api/chat/project", json={"message": "What does this project do?"}
        )
        self.assertEqual(unauthorized.status_code, 401)

        with patch.object(
            backend_app.gemini_service,
            "chat_about_project",
            new_callable=AsyncMock,
            return_value="It helps candidates practice interviews.",
        ) as chat:
            response = self.client.post(
                "/api/chat/project",
                headers=self.user_headers,
                json={
                    "message": "What does this project do?",
                    "history": [{"role": "user", "content": "Hello"}],
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            response.json()["answer"],
            "It helps candidates practice interviews.",
        )
        chat.assert_awaited_once_with(
            message="What does this project do?",
            history=[{"role": "user", "content": "Hello"}],
        )

    def test_chat_accepts_pasted_question_and_trims_long_history(self):
        long_question = "Q" * 2500
        long_answer = "A" * 2500
        with patch.object(
            backend_app.gemini_service,
            "chat_about_project",
            new_callable=AsyncMock,
            return_value="Try structuring your answer with a clear example.",
        ) as chat:
            response = self.client.post(
                "/api/chat/project",
                headers=self.user_headers,
                json={
                    "message": long_question,
                    "history": [{"role": "assistant", "content": long_answer}],
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        chat.assert_awaited_once_with(
            message=long_question,
            history=[{"role": "assistant", "content": long_answer[-2000:]}],
        )

    def test_registration_persists_gender_and_prevents_self_assigning_admin_role(self):
        email = f"gender-{uuid4().hex}@example.com"
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "Gender Test",
                "email": email,
                "password": "secure-password-123",
                "gender": "non_binary",
                "role": "admin",
            },
        )

        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["user"]["gender"], "non_binary")
        self.assertEqual(response.json()["user"]["role"], "user")
        headers = {"Authorization": f"Bearer {response.json()['access_token']}"}

        updated = self.client.patch(
            "/api/users/me",
            headers=headers,
            json={"gender": "female", "role": "admin"},
        )

        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["gender"], "female")
        self.assertEqual(updated.json()["role"], "user")
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == email))
            self.assertEqual(user.gender, "female")
            self.assertEqual(user.role, "user")

    def test_allowlisted_admin_role_is_persisted_and_returned(self):
        admin = self.client.get("/api/users/me", headers=self.admin_headers)

        self.assertEqual(admin.status_code, 200, admin.text)
        self.assertEqual(admin.json()["role"], "admin")
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email == "admin@example.com"))
            self.assertEqual(user.role, "admin")

    def test_allowlisted_account_with_stale_role_is_promoted_on_authentication(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            email = user.email
            user_id = user.id

        os.environ["SUPER_ADMIN_EMAILS"] += f",{email.upper()}"

        response = self.client.get(
            "/api/admin/summary",
            headers=self.user_headers,
        )

        self.assertEqual(response.status_code, 200, response.text)
        with database.SessionLocal() as db:
            user = db.get(User, user_id)
            self.assertEqual(user.role, "admin")

    def test_admin_can_promote_and_demote_non_super_admin_accounts(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            user_id = user.id

        promoted = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"role": "admin"},
        )

        self.assertEqual(promoted.status_code, 200, promoted.text)
        self.assertEqual(promoted.json()["role"], "admin")
        self.assertFalse(promoted.json()["super_admin"])

        self._register(f"other-{uuid4().hex}@example.com")
        with database.SessionLocal() as db:
            other_user = db.scalar(
                select(User).where(User.email.like("other-%"))
            )
            other_user_id = other_user.id

        admin_summary = self.client.get(
            "/api/admin/summary",
            headers=self.user_headers,
        )
        self.assertEqual(admin_summary.status_code, 200, admin_summary.text)

        promoted_by_admin = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"role": "admin"},
        )
        self.assertEqual(promoted_by_admin.status_code, 200, promoted_by_admin.text)
        self.assertEqual(promoted_by_admin.json()["role"], "admin")

        demoted_by_admin = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"role": "user"},
        )
        self.assertEqual(demoted_by_admin.status_code, 200, demoted_by_admin.text)
        self.assertEqual(demoted_by_admin.json()["role"], "user")

        promoted_by_admin = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"role": "admin"},
        )
        self.assertEqual(promoted_by_admin.status_code, 200, promoted_by_admin.text)

        admin_plan = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"plan": "pro", "duration_days": 30},
        )
        self.assertEqual(admin_plan.status_code, 200, admin_plan.text)
        self.assertEqual(admin_plan.json()["plan"], "pro")

        suspended_admin = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"suspended": True},
        )
        self.assertEqual(suspended_admin.status_code, 200, suspended_admin.text)
        self.assertTrue(suspended_admin.json()["suspended"])

        restored_admin = self.client.patch(
            f"/api/admin/users/{other_user_id}",
            headers=self.user_headers,
            json={"suspended": False},
        )
        self.assertEqual(restored_admin.status_code, 200, restored_admin.text)
        self.assertFalse(restored_admin.json()["suspended"])

    def test_admin_cannot_change_their_own_role(self):
        admin_id = self.client.get(
            "/api/users/me",
            headers=self.admin_headers,
        ).json()["id"]

        response = self.client.patch(
            f"/api/admin/users/{admin_id}",
            headers=self.admin_headers,
            json={"role": "user"},
        )

        self.assertEqual(response.status_code, 409)

    def test_regular_user_cannot_assign_admin_role(self):
        with database.SessionLocal() as db:
            admin = db.scalar(select(User).where(User.email == "admin@example.com"))
            admin_id = admin.id

        response = self.client.patch(
            f"/api/admin/users/{admin_id}",
            headers=self.user_headers,
            json={"role": "admin"},
        )

        self.assertEqual(response.status_code, 403)

    def test_role_update_rejects_values_other_than_user_and_admin(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            user_id = user.id

        response = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"role": "super_admin"},
        )

        self.assertEqual(response.status_code, 422)

    def test_existing_users_table_is_upgraded_with_gender_and_role(self):
        engine = create_engine("sqlite+pysqlite://")
        try:
            with engine.begin() as connection:
                connection.exec_driver_sql(
                    "CREATE TABLE users ("
                    "id INTEGER PRIMARY KEY, "
                    "username VARCHAR(80) NOT NULL, "
                    "email VARCHAR(120) NOT NULL, "
                    "password_hash VARCHAR(255) NOT NULL, "
                    "created_at DATETIME NOT NULL)"
                )
                connection.exec_driver_sql(
                    "INSERT INTO users (id, username, email, password_hash, created_at) "
                    "VALUES (1, 'Existing', 'existing@example.com', 'hash', "
                    "'2026-01-01 00:00:00')"
                )

            backend_app._ensure_user_profile_columns(engine)

            with engine.connect() as connection:
                row = connection.execute(
                    text("SELECT gender, role FROM users WHERE id = 1")
                ).one()
            self.assertIsNone(row.gender)
            self.assertEqual(row.role, "user")
        finally:
            engine.dispose()

    def test_admin_allowlist_and_user_search(self):
        denied = self.client.get("/api/admin/summary", headers=self.user_headers)
        self.assertEqual(denied.status_code, 403)

        summary = self.client.get("/api/admin/summary", headers=self.admin_headers)
        self.assertEqual(summary.status_code, 200, summary.text)
        self.assertEqual(summary.json()["total_users"], 2)

        users = self.client.get(
            "/api/admin/users",
            headers=self.admin_headers,
            params={"search": "user-", "limit": 1},
        )
        self.assertEqual(users.status_code, 200, users.text)
        self.assertEqual(users.json()["total"], 1)
        self.assertEqual(len(users.json()["users"]), 1)

    def test_admin_plan_changes_suspend_and_restore(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            user_id = user.id

        plan_response = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"plan": "elite", "duration_days": 45},
        )
        self.assertEqual(plan_response.status_code, 200, plan_response.text)
        self.assertEqual(plan_response.json()["plan"], "elite")

        removed_plan = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"plan": "pre", "duration_days": 45},
        )
        self.assertEqual(removed_plan.status_code, 422)

        suspended = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"suspended": True},
        )
        self.assertEqual(suspended.status_code, 200, suspended.text)
        self.assertTrue(suspended.json()["suspended"])
        blocked = self.client.get("/api/users/me", headers=self.user_headers)
        self.assertEqual(blocked.status_code, 403)

        restored = self.client.patch(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
            json={"suspended": False},
        )
        self.assertEqual(restored.status_code, 200, restored.text)
        self.assertFalse(restored.json()["suspended"])
        allowed = self.client.get("/api/users/me", headers=self.user_headers)
        self.assertEqual(allowed.status_code, 200)

    def test_admin_cannot_suspend_or_delete_an_allowlisted_admin(self):
        with database.SessionLocal() as db:
            admin_id = db.scalar(
                select(User.id).where(User.email == "admin@example.com")
            )

        suspended = self.client.patch(
            f"/api/admin/users/{admin_id}",
            headers=self.admin_headers,
            json={"suspended": True},
        )
        deleted = self.client.delete(
            f"/api/admin/users/{admin_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(suspended.status_code, 409)
        self.assertEqual(deleted.status_code, 409)

    def test_payment_review_activates_subscription_for_super_admin(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            payment = PaymentSubmission(
                user_id=user.id,
                plan="pre",
                amount_rupees=199,
                screenshot=b"receipt",
                screenshot_content_type="image/png",
                status="pending",
            )
            db.add(payment)
            db.commit()
            payment_id = payment.id

        pending = self.client.get(
            "/api/admin/payments/pending",
            headers=self.admin_headers,
        )
        self.assertEqual(pending.status_code, 200, pending.text)
        self.assertEqual(pending.json()[0]["payment_id"], payment_id)
        self.assertEqual(pending.json()[0]["plan"], "legacy_resume")

        with patch.dict(os.environ, {"SUBSCRIPTION_DURATION_DAYS": "30"}):
            reviewed = self.client.post(
                f"/api/admin/payments/{payment_id}/review",
                headers=self.admin_headers,
                json={"decision": "approved"},
            )

        self.assertEqual(reviewed.status_code, 200, reviewed.text)
        self.assertEqual(reviewed.json()["status"], "approved")
        self.assertEqual(reviewed.json()["subscription"]["plan"], "legacy_resume")

    def test_manual_payment_proof_records_reference_and_blocks_reuse(self):
        screenshot = b"\x89PNG\r\n\x1a\nmanual-payment-proof"
        request = {
            "data": {
                "plan": "pro",
                "transaction_reference": "  UTR-2026-001  ",
            },
            "files": {
                "screenshot": ("payment.png", screenshot, "image/png"),
            },
            "headers": self.user_headers,
        }

        submitted = self.client.post("/api/billing/payments", **request)
        duplicate = self.client.post(
            "/api/billing/payments",
            data={"plan": "elite", "transaction_reference": "utr-2026-001"},
            files={"screenshot": ("payment.png", screenshot, "image/png")},
            headers=self.user_headers,
        )
        history = self.client.get(
            "/api/billing/payments",
            headers=self.user_headers,
        )

        self.assertEqual(submitted.status_code, 201, submitted.text)
        self.assertEqual(submitted.json()["amount_rupees"], 299)
        self.assertEqual(submitted.json()["transaction_reference"], "UTR-2026-001")
        self.assertEqual(duplicate.status_code, 409, duplicate.text)
        self.assertEqual(len(history.json()), 1)
        self.assertEqual(
            history.json()[0]["transaction_reference"],
            "UTR-2026-001",
        )

    def test_manual_upi_checkout_returns_configured_payee_and_plan_amount(self):
        with patch.dict(
            os.environ,
            {"UPI_ID": "merchant@example", "UPI_PAYEE_NAME": "InterviewAI"},
        ):
            response = self.client.post(
                "/api/billing/checkout",
                headers=self.user_headers,
                json={"plan": "elite"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        checkout = response.json()
        self.assertEqual(checkout["upi_id"], "merchant@example")
        self.assertEqual(checkout["payee_name"], "InterviewAI")
        self.assertEqual(checkout["amount_rupees"], 599)
        self.assertIn("Complete payment", checkout["instructions"])

    def test_interview_shuffles_selected_categories_and_rotates_question_focus(self):
        selected = ["Frontend", "Database", "AI/ML"]
        with (
            patch.object(
                backend_app,
                "_get_company_intelligence",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_interview_question",
                new_callable=AsyncMock,
                return_value="How did you structure your project?",
            ) as generate_question,
        ):
            response = self.client.post(
                "/interviews/start",
                headers=self.user_headers,
                json={
                    "role_category": "Software Engineer",
                    "sub_role": "Full Stack",
                    "technical_categories": selected,
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        interview = response.json()
        self.assertEqual(set(interview["technical_category_plan"]), set(selected))
        self.assertIn(interview["question_category"], selected)
        self.assertEqual(
            generate_question.await_args.kwargs["question_category"],
            interview["question_category"],
        )

        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview["id"])
            self.assertEqual(
                backend_app._next_session_question_category(session),
                interview["technical_category_plan"][1],
            )

    def test_interview_configures_and_persists_question_count_per_round(self):
        with (
            patch.object(
                backend_app,
                "_get_company_intelligence",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_interview_question",
                new_callable=AsyncMock,
                return_value="How do you design a reliable service?",
            ),
        ):
            response = self.client.post(
                "/interviews/start",
                headers=self.user_headers,
                json={
                    "role_category": "Software Engineer",
                    "sub_role": "Backend",
                    "questions_per_round": 5,
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        interview = response.json()
        self.assertEqual(interview["questions_per_round"], 5)
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview["id"])
            self.assertEqual(
                backend_app._session_questions_per_round(session),
                5,
            )
        history = self.client.get(
            f"/api/interviews/history/{interview['id']}",
            headers=self.user_headers,
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["questions_per_round"], 5)

    def test_interview_start_persists_the_profile_based_round_plan(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                CandidateProfile(
                    user_id=user.id,
                    employment_status="college_student",
                    years_of_experience=1,
                )
            )
            db.commit()

        with (
            patch.object(
                backend_app,
                "_get_company_intelligence",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_interview_question",
                new_callable=AsyncMock,
                return_value="How would you approach this technical problem?",
            ),
        ):
            response = self.client.post(
                "/interviews/start",
                headers=self.user_headers,
                json={
                    "role_category": "Software Engineer",
                    "sub_role": "Backend",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, response.json()["id"])
            self.assertEqual(session.interview_round, "Technical/Screening")
            self.assertEqual(
                backend_app._session_round_plan(session),
                [
                    "Technical/Screening",
                    "Behavioral/HR",
                    "System Design",
                ],
            )

    def test_selected_question_limit_controls_round_transition(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
                interview_round="Technical/Screening",
                questions_count=4,
                total_questions=4,
                round_scores={"Technical/Screening": 8.0},
                transcript=[
                    {"role": "system", "questions_per_round": 5},
                    {
                        "role": "assistant",
                        "content": "How do you design a reliable service?",
                        "round": "Technical/Screening",
                    },
                ],
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        with (
            patch.object(
                backend_app.gemini_service,
                "evaluate_answer",
                new_callable=AsyncMock,
                return_value='{"score": 8, "feedback": "Good reasoning.", "improvements": []}',
            ),
            patch.object(
                backend_app,
                "_generate_session_question",
                new_callable=AsyncMock,
                return_value=("How do you handle a difficult stakeholder?", None),
            ) as generate_question,
        ):
            response = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": "I would validate the requirements, define service boundaries, and add observability.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["round_completed"])
        self.assertEqual(result["next_round"], "Behavioral/HR")
        self.assertEqual(result["questions_asked"], 0)
        self.assertEqual(result["questions_per_round"], 5)
        generate_question.assert_awaited_once()

    def test_round_below_cutoff_ends_session_without_generating_a_question(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
                interview_round="Technical/Screening",
                questions_count=4,
                total_questions=4,
                round_scores={"Technical/Screening": 5.9},
                transcript=[
                    {"role": "system", "questions_per_round": 5},
                    {
                        "role": "assistant",
                        "content": "How do you design a reliable service?",
                        "round": "Technical/Screening",
                    },
                ],
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        with (
            patch.object(
                backend_app.gemini_service,
                "evaluate_answer",
                new_callable=AsyncMock,
                return_value='{"score": 5, "feedback": "Add more detail.", "improvements": []}',
            ),
            patch.object(
                backend_app,
                "_generate_session_question",
                new_callable=AsyncMock,
            ) as generate_question,
            patch.object(
                backend_app,
                "get_memory_service",
                return_value=SimpleNamespace(learn_from_session=AsyncMock()),
            ),
        ):
            response = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": "I would use a server.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["terminated"])
        self.assertFalse(result["round_passed"])
        self.assertEqual(result["overall_status"], "failed")
        self.assertEqual(result["selection_status"], "failed")
        self.assertLess(result["selection_score"], 6)
        self.assertIsNone(result["next_question"])
        self.assertEqual(result["failed_round"], "Technical/Screening")
        generate_question.assert_not_awaited()
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview_id)
            self.assertEqual(session.overall_status, "failed")
            self.assertEqual(
                session.transcript[-1]["completion"]["status"],
                "failed",
            )
            self.assertEqual(
                session.transcript[-1]["completion"]["selection_status"],
                "failed",
            )
        history = self.client.get(
            f"/api/interviews/history/{interview_id}",
            headers=self.user_headers,
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["selection_status"], "failed")

    def test_candidate_can_edit_saved_answer_after_ai_evaluation_failure(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            db.add(
                CandidateProfile(
                    user_id=user.id,
                    employment_status="recent_graduate",
                    years_of_experience=0,
                )
            )
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
                interview_round="Technical/Screening",
                transcript=[
                    {
                        "role": "system",
                        "candidate_profile": {
                            "employment_status": "recent_graduate",
                            "years_of_experience": 0,
                        },
                    },
                    {
                        "role": "assistant",
                        "content": "How would you design a scalable API?",
                        "round": "Technical/Screening",
                        "technical_category": "Backend",
                    }
                ],
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        improved_answer = "I would define the API contract, add pagination, and use caching."
        with (
            patch.object(
                backend_app.gemini_service,
                "evaluate_answer",
                new_callable=AsyncMock,
                side_effect=[
                    RuntimeError("AI provider temporarily unavailable."),
                    '{"score": 8, "feedback": "Clear and practical.", "improvements": []}',
                ],
            ) as evaluate_answer,
            patch.object(
                backend_app,
                "_generate_session_question",
                new_callable=AsyncMock,
                return_value=("How would you test this API?", "Backend"),
            ),
        ):
            first_attempt = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": "I would make an API.",
                },
            )
            self.assertEqual(first_attempt.status_code, 503, first_attempt.text)

            retry = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": improved_answer,
                },
            )

        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(evaluate_answer.await_count, 2)
        self.assertEqual(
            evaluate_answer.await_args.kwargs["answer"],
            improved_answer,
        )
        self.assertIn(
            "Stage: recent graduate",
            evaluate_answer.await_args_list[0].kwargs["candidate_context"],
        )
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview_id)
            answer_turn = next(
                item for item in session.transcript if item.get("role") == "user"
            )
            saved_answer = db.scalar(
                select(UserAnswer).where(UserAnswer.session_id == interview_id)
            )
            self.assertEqual(answer_turn["content"], improved_answer)
            self.assertNotIn("evaluation_pending", answer_turn)
            self.assertEqual(saved_answer.user_answer, improved_answer)

    def test_owner_can_delete_saved_answer_without_affecting_other_users(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
            )
            db.add(session)
            db.flush()
            answer = UserAnswer(
                session_id=session.id,
                question_text="How would you design a scalable API?",
                user_answer="I would add pagination and caching.",
                final_score=8.0,
            )
            db.add(answer)
            db.commit()
            interview_id = session.id
            answer_id = answer.id

        history = self.client.get(
            f"/api/interviews/history/{interview_id}",
            headers=self.user_headers,
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(history.json()["answers"][0]["answer_id"], answer_id)
        self.assertEqual(history.json()["answers"][0]["missing_concepts"], [])

        forbidden = self.client.delete(
            f"/api/interviews/history/{interview_id}/answers/{answer_id}",
            headers=self.admin_headers,
        )
        self.assertEqual(forbidden.status_code, 404, forbidden.text)
        with database.SessionLocal() as db:
            self.assertIsNotNone(db.get(UserAnswer, answer_id))

        deleted = self.client.delete(
            f"/api/interviews/history/{interview_id}/answers/{answer_id}",
            headers=self.user_headers,
        )

        self.assertEqual(deleted.status_code, 204, deleted.text)
        with database.SessionLocal() as db:
            self.assertIsNone(db.get(UserAnswer, answer_id))
            self.assertIsNotNone(db.get(InterviewSession, interview_id))

    def test_owner_can_discard_only_an_unevaluated_pending_answer(self):
        question = {
            "role": "assistant",
            "content": "How would you design a scalable API?",
            "round": "Technical/Screening",
        }
        pending = {
            "role": "user",
            "content": "I would add pagination and caching.",
            "round": "Technical/Screening",
            "evaluation_pending": True,
        }
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
                transcript=[question, pending],
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        forbidden = self.client.delete(
            f"/api/interviews/history/{interview_id}/pending-answer",
            headers=self.admin_headers,
        )
        self.assertEqual(forbidden.status_code, 404, forbidden.text)

        deleted = self.client.delete(
            f"/api/interviews/history/{interview_id}/pending-answer",
            headers=self.user_headers,
        )

        self.assertEqual(deleted.status_code, 204, deleted.text)
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview_id)
            self.assertEqual(session.transcript, [question])

        no_pending_answer = self.client.delete(
            f"/api/interviews/history/{interview_id}/pending-answer",
            headers=self.user_headers,
        )
        self.assertEqual(no_pending_answer.status_code, 409, no_pending_answer.text)

    def test_final_director_answer_completes_interview_without_another_question(self):
        required_rounds = list(
            backend_app.get_rounds_for_role("Software Engineer")
        )
        previous_rounds = required_rounds[:-1]
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            session = InterviewSession(
                user_id=user.id,
                role_category="Software Engineer",
                sub_role="Backend",
                interview_round="Final/Director",
                current_round_number=len(required_rounds),
                questions_count=19,
                total_questions=79,
                rounds_completed=previous_rounds,
                round_scores={round_name: 8.0 for round_name in required_rounds},
                transcript=[
                    {
                        "role": "assistant",
                        "content": "What would your first 90 days look like?",
                        "round": "Final/Director",
                    }
                ],
            )
            db.add(session)
            db.commit()
            interview_id = session.id

        report = {
            "overall_score": 8,
            "final_verdict": "HIRE",
            "strengths": ["Clear strategic thinking"],
            "areas_to_improve": ["Add more delivery metrics"],
            "recruiter_closing_note": "Strong final-round performance.",
        }
        memory_service = SimpleNamespace(learn_from_session=AsyncMock())
        with (
            patch.object(
                backend_app.gemini_service,
                "evaluate_answer",
                new_callable=AsyncMock,
                return_value='{"score": 8, "feedback": "Strong plan.", "improvements": []}',
            ) as evaluate_answer,
            patch.object(
                backend_app.gemini_service,
                "generate_master_report",
                new_callable=AsyncMock,
                side_effect=[
                    RuntimeError("Report provider is temporarily unavailable."),
                    json.dumps(report),
                ],
            ) as generate_report,
            patch.object(
                backend_app.gemini_service,
                "generation_status",
                side_effect=[
                    "OpenRouter (test/evaluator)",
                    "OpenRouter (test/reporter)",
                    "OpenRouter (test/reporter)",
                ],
            ),
            patch.object(
                backend_app,
                "_generate_session_question",
                new_callable=AsyncMock,
            ) as generate_question,
            patch.object(
                backend_app,
                "get_memory_service",
                return_value=memory_service,
            ),
        ):
            first_response = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": "I would align with the team, learn the product, and identify measurable priorities.",
                },
            )
            self.assertEqual(first_response.status_code, 200, first_response.text)
            pending_report = first_response.json()
            self.assertTrue(pending_report["interview_completed"])
            self.assertTrue(pending_report["master_report_pending"])
            self.assertIsNone(pending_report["next_question"])
            self.assertEqual(pending_report["overall_status"], "completed")
            self.assertEqual(pending_report["selection_status"], "selected")
            self.assertEqual(pending_report["selection_score"], 8.0)
            self.assertEqual(
                pending_report["ai_provider_status"],
                "OpenRouter (test/evaluator)",
            )
            self.assertEqual(
                pending_report["report_provider_status"],
                "OpenRouter (test/reporter)",
            )
            saved_pending = self.client.get(
                f"/api/interviews/history/{interview_id}",
                headers=self.user_headers,
            )
            self.assertEqual(saved_pending.status_code, 200, saved_pending.text)
            self.assertTrue(
                saved_pending.json()["transcript"][-1]["report_pending"]
            )
            self.assertEqual(
                saved_pending.json()["transcript"][-1]["report_provider_status"],
                "OpenRouter (test/reporter)",
            )
            self.assertEqual(saved_pending.json()["selection_status"], "selected")

            response = self.client.post(
                "/interviews/submit-answer",
                headers=self.user_headers,
                json={
                    "interview_id": interview_id,
                    "answer": "I would align with the team, learn the product, and identify measurable priorities.",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertTrue(result["interview_completed"])
        self.assertTrue(result["terminated"])
        self.assertEqual(result["overall_status"], "completed")
        self.assertIsNone(result["next_question"])
        self.assertEqual(result["questions_asked"], 20)
        self.assertEqual(result["total_questions"], 80)
        self.assertEqual(result["rounds_completed"], required_rounds)
        self.assertEqual(result["selection_status"], "selected")
        self.assertEqual(result["selection_score"], 8.0)
        self.assertEqual(result["master_report"]["final_verdict"], "HIRE")
        self.assertEqual(
            result["ai_provider_status"],
            "OpenRouter (test/evaluator)",
        )
        self.assertEqual(
            result["report_provider_status"],
            "OpenRouter (test/reporter)",
        )
        generate_question.assert_not_awaited()
        self.assertEqual(evaluate_answer.await_count, 1)
        self.assertEqual(generate_report.await_count, 2)
        with database.SessionLocal() as db:
            session = db.get(InterviewSession, interview_id)
            self.assertEqual(session.overall_status, "completed")
            final_answer = session.transcript[-1]
            self.assertEqual(final_answer["completion"]["status"], "completed")
            self.assertEqual(
                final_answer["completion"]["selection_status"],
                "selected",
            )
            self.assertEqual(
                final_answer["master_report"]["final_verdict"],
                "HIRE",
            )
            self.assertEqual(
                final_answer["ai_provider_status"],
                "OpenRouter (test/evaluator)",
            )
            self.assertEqual(
                final_answer["report_provider_status"],
                "OpenRouter (test/reporter)",
            )
        history = self.client.get(
            f"/api/interviews/history/{interview_id}",
            headers=self.user_headers,
        )
        self.assertEqual(history.status_code, 200, history.text)
        saved_final_answer = history.json()["transcript"][-1]
        self.assertEqual(saved_final_answer["completion"]["status"], "completed")
        self.assertEqual(
            saved_final_answer["completion"]["selection_status"],
            "selected",
        )
        self.assertEqual(saved_final_answer["master_report"]["final_verdict"], "HIRE")
        self.assertEqual(history.json()["selection_status"], "selected")
        self.assertEqual(history.json()["selection_score"], 8.0)
        history_list = self.client.get(
            "/api/interviews/history",
            headers=self.user_headers,
        )
        self.assertEqual(history_list.status_code, 200, history_list.text)
        saved_session = next(
            item
            for item in history_list.json()
            if item["session_id"] == interview_id
        )
        self.assertEqual(saved_session["selection_status"], "selected")
        self.assertEqual(
            saved_final_answer["report_provider_status"],
            "OpenRouter (test/reporter)",
        )

    def test_resume_categories_auto_detect_from_skills_and_projects(self):
        resume_text = (
            "Professional Experience\n"
            "Built a React frontend and FastAPI backend using MySQL.\n"
            "Project: developed a machine learning recommendation tool."
        )
        with (
            patch.object(
                backend_app,
                "_extract_resume_text",
                return_value=resume_text,
            ),
            patch.object(
                backend_app,
                "_get_company_intelligence",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch.object(
                backend_app.gemini_service,
                "generate_interview_question",
                new_callable=AsyncMock,
                return_value="Tell me about the recommendation project.",
            ) as generate_question,
        ):
            response = self.client.post(
                "/interviews/upload-resume",
                headers=self.user_headers,
                data={
                    "role_category": "Software Engineer",
                    "sub_role": "Full Stack",
                },
                files={"file": ("resume.pdf", b"%PDF-1.7", "application/pdf")},
            )

        self.assertEqual(response.status_code, 200, response.text)
        categories = response.json()["technical_category_plan"]
        self.assertTrue({"Frontend", "Backend", "Database", "AI/ML", "Project Deep Dive"}.issubset(categories))
        self.assertIn("React frontend", generate_question.await_args.kwargs["resume_text"])

    def test_delete_removes_account_and_related_relational_data(self):
        with database.SessionLocal() as db:
            user = db.scalar(select(User).where(User.email.like("user-%")))
            user_id = user.id
            now = datetime.now(timezone.utc)
            interview = InterviewSession(
                user_id=user_id,
                role_category="Engineering",
                sub_role="Backend Engineer",
            )
            db.add(
                Subscription(user_id=user_id, plan="pre", status="active",
                             started_at=now, expires_at=now + timedelta(days=30))
            )
            db.add_all(
                [
                    interview,
                    CandidateProfile(
                        user_id=user_id, employment_status="employed"
                    ),
                    ResumeDocument(
                        user_id=user_id,
                        template_id="classic-navy",
                        title="Test resume",
                        content={},
                    ),
                    DevelopmentWorkflow(
                        user_id=user_id, task_description="Test workflow"
                    ),
                    PaymentSubmission(
                        user_id=user_id,
                        plan="pre",
                        amount_rupees=199,
                        screenshot=b"receipt",
                        screenshot_content_type="image/png",
                        status="pending",
                    ),
                    UserAccessControl(
                        user_id=user_id,
                        suspended=False,
                        updated_by="admin@example.com",
                    ),
                ]
            )
            db.flush()
            db.add(
                UserAnswer(
                    session_id=interview.id,
                    question_text="A question?",
                    user_answer="An answer.",
                    final_score=7,
                )
            )
            db.add(
                CodingRoundLedger(
                    session_id=interview.id,
                    user_id=user_id,
                )
            )
            db.commit()

        response = self.client.delete(
            f"/api/admin/users/{user_id}",
            headers=self.admin_headers,
        )

        self.assertEqual(response.status_code, 204, response.text)
        with database.SessionLocal() as db:
            self.assertIsNone(db.get(User, user_id))
            for model in (
                CandidateProfile,
                CodingRoundLedger,
                DevelopmentWorkflow,
                InterviewSession,
                PaymentSubmission,
                ResumeDocument,
                Subscription,
                UserAccessControl,
            ):
                self.assertIsNone(
                    db.scalar(select(model).where(model.user_id == user_id)),
                    model.__name__,
                )
            self.assertEqual(
                db.scalar(select(UserAnswer).where(UserAnswer.session_id == interview.id)),
                None,
            )

if __name__ == "__main__":
    unittest.main()
