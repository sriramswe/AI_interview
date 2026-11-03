
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


def utc_now():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    username: Mapped[str] = mapped_column(String(80), nullable=False)
    email: Mapped[str] = mapped_column(
        String(120), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "created_at": self.created_at.isoformat(),
        }

    def to_public_dict(self) -> dict:
        # Never expose password_hash in API responses.
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
        }


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    role: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    category: Mapped[str] = mapped_column(
        String(50), nullable=False
    )
    difficulty: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer: Mapped[str] = mapped_column(Text, nullable=False)
    key_concepts: Mapped[str] = mapped_column(
        Text, nullable=False, default=""
    )

    answers: Mapped[list["UserAnswer"]] = relationship(
        "UserAnswer",
        back_populates="question",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "role": self.role,
            "category": self.category,
            "difficulty": self.difficulty,
            "question_text": self.question_text,
            "key_concepts": [
                item.strip()
                for item in self.key_concepts.split(",")
                if item.strip()
            ],
        }


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default="Technical", nullable=False
    )
    total_questions: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    average_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    overall_status: Mapped[str] = mapped_column(
        String(30), default="completed", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    user: Mapped["User"] = relationship(
        "User", back_populates="sessions"
    )
    answers: Mapped[list["UserAnswer"]] = relationship(
        "UserAnswer",
        back_populates="session",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "role": self.role,
            "difficulty": self.difficulty,
            "category": self.category,
            "total_questions": self.total_questions,
            "average_score": round(self.average_score, 2),
            "overall_status": self.overall_status,
            "created_at": self.created_at.isoformat(),
        }


class UserAnswer(Base):
    __tablename__ = "user_answers"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_sessions.id"), index=True, nullable=False
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id"), index=True, nullable=False
    )
    user_answer: Mapped[str] = mapped_column(Text, nullable=False)
    similarity_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    keyword_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    final_score: Mapped[float] = mapped_column(
        Float, nullable=False
    )
    missing_concepts: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    feedback: Mapped[str] = mapped_column(
        Text, default="", nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession", back_populates="answers"
    )
    question: Mapped["Question"] = relationship(
        "Question", back_populates="answers"
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "question_id": self.question_id,
            "question_text": (
                self.question.question_text if self.question else ""
            ),
            "user_answer": self.user_answer,
            "similarity_score": round(self.similarity_score, 2),
            "keyword_score": round(self.keyword_score, 2),
            "final_score": round(self.final_score, 2),
            "missing_concepts": [
                item.strip()
                for item in self.missing_concepts.split(",")
                if item.strip()
            ],
            "feedback": self.feedback,
            "created_at": self.created_at.isoformat(),
        }
