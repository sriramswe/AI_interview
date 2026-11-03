from datetime import datetime
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=6, max_length=128)
    gender: Literal[
        "female", "male", "non_binary", "prefer_not_to_say"
    ] | None = None

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v:
            raise ValueError("A valid email address is required.")
        return v

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_optional_gender(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def normalize_login_email(cls, value: str) -> str:
        return value.strip().lower()


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=80)
    email: str | None = Field(default=None, min_length=3, max_length=120)
    gender: Literal[
        "female", "male", "non_binary", "prefer_not_to_say"
    ] | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Username cannot be empty.")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        local, separator, domain = value.partition("@")
        if not separator or not local or "." not in domain:
            raise ValueError("A valid email address is required.")
        return value

    @field_validator("gender", mode="before")
    @classmethod
    def normalize_optional_gender(cls, value: str | None) -> str | None:
        return value.strip() or None if isinstance(value, str) else value


class CompanyDiscoveryRequest(BaseModel):
    company: str = Field(min_length=1, max_length=255)
    job_description: str | None = Field(default=None, max_length=20000)
    geography: str | None = Field(default=None, max_length=120)

    @field_validator("company", "geography")
    @classmethod
    def normalize_discovery_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        if not clean:
            raise ValueError("Company and region cannot be blank.")
        return clean


class GoogleLoginRequest(BaseModel):
    token: str = Field(min_length=1)


class DevelopmentWorkflowCreate(BaseModel):
    task_description: str = Field(min_length=1, max_length=10000)

    @field_validator("task_description")
    @classmethod
    def reject_blank_workflow_task(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Task description cannot be blank.")
        return clean


class DevelopmentTestResult(BaseModel):
    passed: bool
    summary: str = Field(min_length=1, max_length=20000)

    @field_validator("summary")
    @classmethod
    def reject_blank_test_summary(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Test summary cannot be blank.")
        return clean


class DevelopmentDeploymentConfirmation(BaseModel):
    deployment_url: AnyHttpUrl | None = None
    notes: str | None = Field(default=None, max_length=5000)


class DevelopmentMonitoringReport(BaseModel):
    status: Literal["healthy", "degraded"]
    details: str = Field(min_length=1, max_length=20000)

    @field_validator("details")
    @classmethod
    def reject_blank_monitoring_details(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Monitoring details cannot be blank.")
        return clean


class SubscriptionCheckoutRequest(BaseModel):
    plan: Literal["pro", "elite"]


class ResumeExperienceInput(BaseModel):
    role: str = Field(default="", max_length=160)
    company: str = Field(default="", max_length=160)
    dates: str = Field(default="", max_length=100)
    description: str = Field(default="", max_length=5000)


class ResumeEducationInput(BaseModel):
    degree: str = Field(default="", max_length=160)
    institution: str = Field(default="", max_length=160)
    dates: str = Field(default="", max_length=100)
    details: str = Field(default="", max_length=2000)


class ResumeProjectInput(BaseModel):
    name: str = Field(default="", max_length=160)
    link: str = Field(default="", max_length=500)
    description: str = Field(default="", max_length=3000)


class ResumeContentInput(BaseModel):
    full_name: str = Field(default="", max_length=120)
    headline: str = Field(default="", max_length=160)
    email: str = Field(default="", max_length=160)
    phone: str = Field(default="", max_length=60)
    location: str = Field(default="", max_length=160)
    website: str = Field(default="", max_length=500)
    summary: str = Field(default="", max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=80)
    experience: list[ResumeExperienceInput] = Field(default_factory=list, max_length=30)
    education: list[ResumeEducationInput] = Field(default_factory=list, max_length=20)
    projects: list[ResumeProjectInput] = Field(default_factory=list, max_length=30)
    raw_resume_text: str = Field(default="", max_length=30000)


class ResumeCreateRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=80)
    title: str = Field(default="My resume", min_length=1, max_length=160)
    source: Literal["template", "upload"] = "template"
    content: ResumeContentInput

    @field_validator("title")
    @classmethod
    def reject_blank_resume_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Resume title cannot be blank.")
        return clean


class ResumeUpdateRequest(BaseModel):
    template_id: str = Field(min_length=1, max_length=80)
    title: str = Field(default="My resume", min_length=1, max_length=160)
    content: ResumeContentInput

    @field_validator("title")
    @classmethod
    def reject_blank_updated_resume_title(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Resume title cannot be blank.")
        return clean


class PaymentReviewRequest(BaseModel):
    decision: Literal["approved", "rejected"]
    review_note: str | None = Field(default=None, max_length=1000)


class ProjectChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)

    @field_validator("content", mode="before")
    @classmethod
    def limit_project_chat_history(cls, value: object) -> object:
        if isinstance(value, str) and len(value) > 2000:
            return value[-2000:]
        return value

    @field_validator("content")
    @classmethod
    def reject_blank_chat_turn(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Chat messages cannot be blank.")
        return clean


class ProjectChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=5000)
    history: list[ProjectChatTurn] = Field(default_factory=list, max_length=10)

    @field_validator("message")
    @classmethod
    def reject_blank_project_question(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Ask a non-empty question.")
        return clean


class AdminUserUpdate(BaseModel):
    suspended: bool | None = None
    plan: Literal["free", "pro", "elite"] | None = None
    role: Literal["user", "admin"] | None = None
    duration_days: int = Field(default=30, ge=1, le=3650)


class QuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role: str
    category: str
    difficulty: str
    question_text: str
    key_concepts: list[str]


class QuestionCreate(BaseModel):
    role: str
    category: str
    difficulty: str
    question_text: str
    reference_answer: str
    key_concepts: str


class CandidateProfile(BaseModel):
    employment_status: Literal[
        "school_student",
        "college_student",
        "employed",
        "unemployed",
        "career_changer",
        "recent_graduate",
        "other",
    ]
    education_level: str | None = Field(default=None, max_length=120)
    institution: str | None = Field(default=None, max_length=160)
    field_of_study: str | None = Field(default=None, max_length=120)
    current_role: str | None = Field(default=None, max_length=120)
    years_of_experience: float | None = Field(default=None, ge=0, le=60)

    @field_validator("education_level", "institution", "field_of_study", "current_role")
    @classmethod
    def normalize_optional_profile_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        clean = value.strip()
        return clean or None


class CandidateProfileResponse(CandidateProfile):
    updated_at: datetime


class InterviewCreate(BaseModel):
    role_category: str = Field(min_length=1, max_length=120)
    sub_role: str = Field(min_length=1, max_length=120)
    difficulty_level: int = Field(default=1, ge=1, le=5)
    questions_per_round: Literal[5, 10, 20] = 20
    target_company: str | None = Field(default=None, max_length=255)
    target_geography: str | None = Field(default=None, max_length=120)
    is_panel: bool = False
    job_description: str | None = None
    interviewer_name: str = Field(default="Adinath", max_length=120)
    candidate_profile: CandidateProfile | None = None
    technical_categories: list[
        Literal[
            "Frontend",
            "Backend",
            "Database",
            "AI/ML",
            "Cloud & DevOps",
            "Testing",
            "System Design",
            "Security",
            "Project Deep Dive",
        ]
    ] = Field(default_factory=list, max_length=8)

    @field_validator("technical_categories")
    @classmethod
    def unique_technical_categories(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("Technical categories must not contain duplicates.")
        return value


class PracticeCreate(BaseModel):
    role: str = Field(min_length=1, max_length=100)
    difficulty: str = Field(min_length=1, max_length=50)
    category: str = Field(default="Technical", min_length=1, max_length=50)


class ResumeRewriteRequest(BaseModel):
    resume_text: str = Field(min_length=1, max_length=30000)
    job_description: str = Field(min_length=1, max_length=20000)

    @field_validator("resume_text", "job_description")
    @classmethod
    def reject_blank_resume_rewrite_fields(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Resume text and job description cannot be blank.")
        return clean


class PracticeAnswerSubmit(BaseModel):
    interview_id: int = Field(gt=0)
    question_id: int | None = Field(default=None, gt=0)
    answer: str = Field(min_length=1, max_length=20000)

    @field_validator("answer")
    @classmethod
    def reject_blank_practice_answer(cls, value: str) -> str:
        answer = value.strip()
        if not answer:
            raise ValueError("Submitted answer cannot be blank.")
        return answer


class InterviewResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    role_category: str
    sub_role: str
    difficulty_level: int
    difficulty: str
    target_company: str | None = None
    target_geography: str | None = None
    interviewer_name: str
    first_question: str
    question_category: str | None = None
    technical_category_plan: list[str] = Field(default_factory=list)
    questions_per_round: Literal[5, 10, 20] = 20
    resume_analysis: dict | str | None = None
    company_intelligence: dict | None = None
    created_at: datetime


class AnswerSubmit(BaseModel):
    interview_id: int = Field(gt=0)
    answer: str = Field(min_length=1, max_length=20000)
    answer_duration_seconds: float | None = Field(default=None, gt=0, le=3600)

    @field_validator("answer")
    @classmethod
    def reject_blank(cls, val: str) -> str:
        clean = val.strip()
        if not clean:
            raise ValueError("Submitted answer cannot be blank.")
        return clean


class AnswerRetry(BaseModel):
    answer: str = Field(min_length=1, max_length=20000)

    @field_validator("answer")
    @classmethod
    def reject_blank_retry(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Submitted answer cannot be blank.")
        return clean


class CodingProblemRequest(BaseModel):
    language: Literal["python", "javascript", "java", "cpp"] = "python"


class CodingSubmission(BaseModel):
    code: str = Field(min_length=1, max_length=30000)
    explanation: str = Field(min_length=1, max_length=8000)

    @field_validator("code", "explanation")
    @classmethod
    def reject_blank_coding_fields(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("Code and explanation cannot be blank.")
        return clean


class RecommendationOut(BaseModel):
    topic: str
    advice: str
    recommended_questions: list[str]


class ScoreTrendOut(BaseModel):
    session_id: int
    date: datetime
    role: str
    score: float


class PerformanceAnalytics(BaseModel):
    total_interviews: int
    total_questions_attempted: int
    overall_average_score: float
    weakest_areas: list[str]
    recommendations: list[RecommendationOut]
    completed_interviews: int = 0
    score_trend: list[ScoreTrendOut] = Field(default_factory=list)
    round_averages: dict[str, float] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    average_filler_rate_per_100_words: float | None = None
    average_speaking_pace_wpm: float | None = None
    vibe_averages: dict[str, float] = Field(default_factory=dict)