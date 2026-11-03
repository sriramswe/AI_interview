import random
import re

from utils.resume_parser import find_resume_skills


TECHNICAL_CATEGORIES = (
    "Frontend",
    "Backend",
    "Database",
    "AI/ML",
    "Cloud & DevOps",
    "Testing",
    "System Design",
    "Security",
    "Project Deep Dive",
)

CATEGORY_SKILLS = {
    "Frontend": {
        "html", "html5", "css", "css3", "javascript", "typescript", "react",
        "react.js", "next.js", "vue", "vue.js", "angular", "svelte", "redux",
        "zustand", "tailwind", "tailwind css", "webpack", "vite",
    },
    "Backend": {
        "python", "java", "javascript", "typescript", "golang", "go", "ruby",
        "rust", "php", "kotlin", "scala", "fastapi", "flask", "django",
        "express", "express.js", "node.js", "nodejs", "nestjs", "spring boot",
        "asp.net", "laravel", "ruby on rails", "rest api", "restful api", "grpc",
        "microservices",
    },
    "Database": {
        "sql", "mysql", "postgresql", "postgres", "mongodb", "redis",
        "elasticsearch", "sqlite", "dynamodb", "cassandra", "supabase",
        "firebase", "prisma", "sqlalchemy", "vector database",
    },
    "AI/ML": {
        "machine learning", "deep learning", "nlp", "computer vision", "llm",
        "genai", "generative ai", "pandas", "numpy", "scikit-learn",
        "tensorflow", "pytorch", "hugging face", "langchain", "data science",
        "data analysis",
    },
    "Cloud & DevOps": {
        "docker", "kubernetes", "aws", "azure", "gcp", "google cloud", "ci/cd",
        "ci cd", "jenkins", "github actions", "terraform", "ansible", "linux",
        "nginx", "serverless",
    },
    "Testing": {"unit testing", "pytest", "jest", "cypress", "postman"},
    "System Design": {"system design", "microservices", "grpc"},
    "Security": {"oauth", "authentication", "authorization", "encryption"},
}

CATEGORY_ROLE_TERMS = {
    "Frontend": ("frontend", "front-end", "ui", "web developer"),
    "Backend": ("backend", "back-end", "api developer", "server-side"),
    "Database": ("database", "data engineer", "sql developer"),
    "AI/ML": ("ai", "machine learning", "ml engineer", "data scientist"),
    "Cloud & DevOps": ("devops", "cloud engineer", "site reliability", "sre"),
    "Testing": ("qa engineer", "test engineer", "quality assurance"),
    "System Design": ("architect", "staff engineer", "system design"),
    "Security": ("security engineer", "application security", "cybersecurity"),
}


def resolve_technical_categories(
    requested_categories: list[str] | None,
    *,
    resume_text: str | None,
    role: str,
) -> list[str]:
    requested = list(dict.fromkeys(requested_categories or []))
    if len(requested) > 8:
        raise ValueError("Select no more than 8 technical categories.")
    invalid = [category for category in requested if category not in TECHNICAL_CATEGORIES]
    if invalid:
        raise ValueError(f"Unsupported technical categories: {', '.join(invalid)}")
    if requested:
        return requested

    skills = set(find_resume_skills(resume_text or ""))
    role_text = role.casefold()
    detected = [
        category
        for category in TECHNICAL_CATEGORIES
        if category != "Project Deep Dive"
        and (
            skills.intersection(CATEGORY_SKILLS.get(category, set()))
            or any(term in role_text for term in CATEGORY_ROLE_TERMS.get(category, ()))
        )
    ]
    if resume_text and re.search(r"\b(project|built|developed|implemented)\b", resume_text, re.I):
        detected.append("Project Deep Dive")
    if not detected:
        detected = ["Backend", "Frontend", "Database"]
    return list(dict.fromkeys(detected))


def shuffled_category_plan(categories: list[str]) -> list[str]:
    plan = list(dict.fromkeys(categories))
    random.SystemRandom().shuffle(plan)
    return plan
