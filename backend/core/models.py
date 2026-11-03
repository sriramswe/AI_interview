from datetime import datetime, timezone
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import quoted_name
from core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    gender: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(
        String(20), default="user", server_default="user", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    
    sessions: Mapped[list["InterviewSession"]] = relationship("InterviewSession", back_populates="user", cascade="all, delete-orphan")
    candidate_profile: Mapped["CandidateProfile | None"] = relationship(
        "CandidateProfile",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    def to_public_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "gender": self.gender,
            "role": self.role,
        }


class UserAccessControl(Base):
    __tablename__ = "user_access_controls"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    suspended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    updated_by: Mapped[str] = mapped_column(String(120), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )


class CandidateProfile(Base):
    __tablename__ = "candidate_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    employment_status: Mapped[str] = mapped_column(String(40), nullable=False)
    education_level: Mapped[str | None] = mapped_column(String(120))
    institution: Mapped[str | None] = mapped_column(String(160))
    field_of_study: Mapped[str | None] = mapped_column(String(120))
    current_role: Mapped[str | None] = mapped_column(
        quoted_name("current_role", True), String(120)
    )
    years_of_experience: Mapped[float | None] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="candidate_profile")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    role: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # Technical, HR, Scenario
    difficulty: Mapped[str] = mapped_column(String(50), index=True, nullable=False)  # Beginner, Intermediate, Advanced
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=False)
    key_concepts: Mapped[str] = mapped_column(Text, nullable=False)

    answers: Mapped[list["UserAnswer"]] = relationship("UserAnswer", back_populates="question")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    
    role_category: Mapped[str] = mapped_column(String(120), nullable=False)
    sub_role: Mapped[str] = mapped_column(String(120), nullable=False)
    difficulty_level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), default="Intermediate", nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="Technical", nullable=False)
    target_company: Mapped[str | None] = mapped_column(String(255))
    is_panel: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    interviewer_name: Mapped[str] = mapped_column(String(120), default="Adinath", nullable=False)
    job_description: Mapped[str | None] = mapped_column(Text)
    resume_text: Mapped[str | None] = mapped_column(Text)
    resume_analysis: Mapped[dict | None] = mapped_column(JSON)
    interview_round: Mapped[str] = mapped_column(String(120), default="Technical", nullable=False)
    current_round_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    questions_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    transcript: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    round_scores: Mapped[dict[str, float]] = mapped_column(JSON, default=dict, nullable=False)
    rounds_completed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[float | None] = mapped_column(Float, default=0.0)
    average_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(30), default="in_progress", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="sessions")
    answers: Mapped[list["UserAnswer"]] = relationship("UserAnswer", back_populates="session", cascade="all, delete-orphan")


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id", ondelete="CASCADE"), index=True, nullable=False)
    question_id: Mapped[int | None] = mapped_column(ForeignKey("questions.id", ondelete="SET NULL"), nullable=True)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    keyword_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    missing_concepts: Mapped[str] = mapped_column(Text, default="", nullable=False)
    feedback: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )

    session: Mapped["InterviewSession"] = relationship("InterviewSession", back_populates="answers")
    question: Mapped["Question | None"] = relationship("Question", back_populates="answers")


class CodingRoundLedger(Base):
    __tablename__ = "coding_round_ledgers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    ledger_data: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    jti: Mapped[str] = mapped_column(String(36), primary_key=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PaymentSubmission(Base):
    __tablename__ = "payment_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    plan: Mapped[str] = mapped_column(String(20), nullable=False)
    amount_rupees: Mapped[int] = mapped_column(Integer, nullable=False)
    transaction_reference: Mapped[str | None] = mapped_column(String(120))
    screenshot: Mapped[bytes] = mapped_column(MEDIUMBLOB, nullable=False)
    screenshot_content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    review_note: Mapped[str | None] = mapped_column(Text)
    reviewer_email: Mapped[str | None] = mapped_column(String(120))
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped["User"] = relationship("User")


class ResumeDocument(Base):
    __tablename__ = "resume_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    template_id: Mapped[str] = mapped_column(String(80), nullable=False)
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    source: Mapped[str] = mapped_column(String(20), default="template", nullable=False)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PlanUsage(Base):
    __tablename__ = "plan_usage"
    __table_args__ = (
        Index("ix_plan_usage_user_type_created", "user_id", "usage_type", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    usage_type: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class DevelopmentWorkflow(Base):
    __tablename__ = "development_workflows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    task_description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="planning")
    plan: Mapped[str | None] = mapped_column(Text)
    agent_outputs: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    test_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    test_results: Mapped[list[dict]] = mapped_column(JSON, default=list, nullable=False)
    deployment: Mapped[dict | None] = mapped_column(JSON)
    monitoring: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )