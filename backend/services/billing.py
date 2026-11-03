from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import models


PLAN_PRICES_RUPEES = {"pro": 299, "elite": 599}
PLAN_RANK = {"free": 0, "pro": 1, "legacy_resume": 1, "elite": 2}
PLAN_QUOTAS = {
    "free": {
        "interviews": 3,
        "resume_analyses": 1,
        "company_questions": 0,
    },
    "pro": {
        "interviews": 20,
        "resume_analyses": 5,
        "company_questions": 30,
    },
    "legacy_resume": {
        "interviews": None,
        "resume_analyses": None,
        "company_questions": 30,
    },
    "elite": {
        "interviews": None,
        "resume_analyses": None,
        "company_questions": None,
    },
}


def normalize_plan(plan: str) -> str:
    return "legacy_resume" if plan == "pre" else plan


def get_active_subscription(
    db: Session, user_id: int
) -> models.Subscription | None:
    return db.scalar(
        select(models.Subscription)
        .where(
            models.Subscription.user_id == user_id,
            models.Subscription.status == "active",
            models.Subscription.expires_at > datetime.now(timezone.utc),
        )
        .order_by(models.Subscription.expires_at.desc())
    )


def get_user_plan(db: Session, user_id: int) -> str:
    subscription = get_active_subscription(db, user_id)
    return normalize_plan(subscription.plan) if subscription else "free"


def build_upi_payment_uri(plan: str, upi_id: str, payee_name: str) -> str:
    amount = PLAN_PRICES_RUPEES[plan]
    query = urlencode(
        {
            "pa": upi_id,
            "pn": payee_name,
            "am": f"{amount:.2f}",
            "cu": "INR",
            "tn": f"InterviewAI {plan.title()} subscription",
        }
    )
    return f"upi://pay?{query}"


def activate_subscription(
    db: Session,
    payment: models.PaymentSubmission,
    reviewer_email: str,
    review_note: str | None,
    duration_days: int,
) -> models.Subscription:
    now = datetime.now(timezone.utc)
    active_subscriptions = db.scalars(
        select(models.Subscription).where(
            models.Subscription.user_id == payment.user_id,
            models.Subscription.status == "active",
        )
    ).all()
    for existing in active_subscriptions:
        existing.status = "expired"

    subscription = models.Subscription(
        user_id=payment.user_id,
        plan=normalize_plan(payment.plan),
        status="active",
        started_at=now,
        expires_at=now + timedelta(days=duration_days),
    )
    payment.status = "approved"
    payment.review_note = review_note
    payment.reviewer_email = reviewer_email
    payment.reviewed_at = now
    db.add(subscription)
    return subscription
