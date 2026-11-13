from collections.abc import Sequence
import re


ROUND_SEQUENCES: dict[str, tuple[str, ...]] = {
    "technology": (
        "Technical/Screening",
        "Behavioral/HR",
        "System Design",
        "Managerial",
        "Final/Director",
    ),
    "healthcare": (
        "Healthcare Screening",
        "Clinical/Situational",
        "Patient Interaction",
        "Managerial",
        "Final/Director",
    ),
    "business": (
        "Business Case Study",
        "Analytical/Market Analysis",
        "Behavioral/HR",
        "Managerial",
        "Final/Director",
    ),
    "finance": (
        "Finance Screening",
        "Financial Modeling/Case Study",
        "Risk & Compliance",
        "Managerial",
        "Final/Director",
    ),
    "creative": (
        "Portfolio Review",
        "Design Thinking",
        "Collaboration/Stakeholders",
        "Managerial",
        "Final/Director",
    ),
    "sales": (
        "Sales Pitch Simulation",
        "Objection Handling",
        "Customer/Market Strategy",
        "Managerial",
        "Final/Director",
    ),
    "education": (
        "Teaching Demonstration",
        "Education Methodology",
        "Learner/Parent Scenarios",
        "Managerial",
        "Final/Director",
    ),
    "legal": (
        "Legal Screening",
        "Case Analysis",
        "Ethics/Client Scenarios",
        "Managerial",
        "Final/Director",
    ),
    "hospitality": (
        "Service Screening",
        "Customer Service Scenarios",
        "Hospitality Operations",
        "Managerial",
        "Final/Director",
    ),
    "social_services": (
        "Case Management Screening",
        "Client/Community Scenarios",
        "Ethics/Safeguarding",
        "Managerial",
        "Final/Director",
    ),
    "construction": (
        "Construction/Trade Screening",
        "Project/Site Scenario",
        "Safety & Quality",
        "Managerial",
        "Final/Director",
    ),
    "science": (
        "Research Methods",
        "Experimental/Analytical Design",
        "Technical/Domain Review",
        "Collaboration/Stakeholders",
        "Final/Director",
    ),
    "hr": (
        "HR Screening",
        "People/Employee Scenarios",
        "Behavioral/HR",
        "Managerial",
        "Final/Director",
    ),
}

DOMAIN_TERMS: dict[str, tuple[str, ...]] = {
    "hr": (
        "hr", "human resources", "hr manager", "hr generalist", "recruiter", "recruiting",
        "talent acquisition", "people operations",
    ),
    "healthcare": (
        "healthcare", "health care", "clinical", "medical", "nurse", "nursing",
        "physician", "patient care", "pharmacy", "dentist", "therapist",
    ),
    "finance": (
        "finance", "financial", "accounting", "accountant", "banking", "investment",
        "auditor", "audit", "actuary", "tax analyst", "risk analyst",
    ),
    "legal": (
        "legal", "lawyer", "attorney", "counsel", "paralegal", "law firm",
    ),
    "creative": (
        "creative", "designer", "design", "ux", "ui", "artist", "animator",
        "portfolio", "graphic",
    ),
    "education": (
        "education", "teacher", "teaching", "instructor", "professor", "curriculum",
        "tutor", "learning specialist",
    ),
    "hospitality": (
        "hospitality", "hotel", "tourism", "concierge", "guest services", "chef",
        "restaurant",
    ),
    "social_services": (
        "social work", "social services", "case worker", "case manager",
        "community services", "counselor", "child protection",
    ),
    "construction": (
        "construction", "electrician", "plumber", "tradesperson", "civil engineer",
        "site manager", "foreman", "carpenter",
    ),
    "science": (
        "scientist", "researcher", "research scientist", "laboratory", "lab technician",
        "biologist", "chemist", "physicist",
    ),
    "sales": (
        "sales", "marketing", "account executive", "business development",
        "customer success", "brand manager",
    ),
    "business": (
        "business", "management consultant", "consultant", "strategy", "product manager",
        "market analyst", "operations manager",
    ),
}

TECHNICAL_ROLE_TERMS = (
    "software",
    "developer",
    "programmer",
    "engineer",
    "technical",
    "devops",
    "data scientist",
    "machine learning",
    "cybersecurity",
    "systems architect",
)

FRESHER_INAPPROPRIATE_ROUNDS = frozenset({"Managerial", "Final/Director"})


def _contains_domain_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(
        re.search(
            r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])",
            text,
        )
        for term in terms
    )


ROUND_CRITERIA: dict[str, tuple[str, ...]] = {
    "Technical/Screening": (
        "Role fundamentals and relevant technical depth",
        "Problem-solving approach and communication",
        "Coding questions only when the role requires coding",
    ),
    "Behavioral/HR": (
        "Use of Situation, Task, Action, and Result",
        "Ownership, collaboration, and reflection",
        "Evidence-backed examples",
    ),
    "System Design": (
        "Requirements and constraints",
        "Architecture, scalability, reliability, and security",
        "Trade-offs and clear communication",
    ),
    "Managerial": (
        "Leadership and team development",
        "Conflict resolution and accountability",
        "Prioritization and delivery",
    ),
    "Final/Director": (
        "Strategic thinking and long-term vision",
        "Company and role alignment",
        "Executive presence and offer/salary negotiation when appropriate",
    ),
    "Healthcare Screening": (
        "Relevant clinical or healthcare fundamentals",
        "Patient safety and professional judgment",
    ),
    "Clinical/Situational": (
        "Assessment and prioritization",
        "Evidence-based decisions and escalation",
        "Patient safety and ethical practice",
    ),
    "Patient Interaction": (
        "Empathy and clear communication",
        "Respect for patient needs and privacy",
        "De-escalation and culturally responsive care",
    ),
    "Business Case Study": (
        "Problem framing and clarifying questions",
        "Structured analysis and assumptions",
        "Recommendation supported by evidence",
    ),
    "Analytical/Market Analysis": (
        "Market sizing and data interpretation",
        "Commercial judgment and assumptions",
        "Actionable recommendations",
    ),
    "Finance Screening": (
        "Accounting and finance fundamentals relevant to the role",
        "Accuracy, judgment, and clear assumptions",
    ),
    "Financial Modeling/Case Study": (
        "Model structure, inputs, and assumptions",
        "Financial reasoning and sensitivity analysis",
        "Interpretation of risks and results",
    ),
    "Risk & Compliance": (
        "Risk identification and mitigation",
        "Regulatory and ethical judgment",
        "Escalation and documentation",
    ),
    "Portfolio Review": (
        "Problem definition and user or audience needs",
        "Quality of craft and rationale",
        "Evidence of impact and iteration",
    ),
    "Design Thinking": (
        "Research and problem framing",
        "Ideation, prototyping, and iteration",
        "Accessibility and validation",
    ),
    "Collaboration/Stakeholders": (
        "Cross-functional communication",
        "Handling feedback and trade-offs",
        "Alignment on outcomes",
    ),
    "Sales Pitch Simulation": (
        "Discovery and value articulation",
        "Audience-aware pitch structure",
        "Ethical, customer-focused persuasion",
    ),
    "Objection Handling": (
        "Active listening and clarification",
        "Evidence-based response",
        "Respectful next-step negotiation",
    ),
    "Customer/Market Strategy": (
        "Customer segmentation and needs",
        "Pipeline or campaign prioritization",
        "Outcome measurement",
    ),
    "Teaching Demonstration": (
        "Clear learning objective and lesson structure",
        "Accessible, engaging explanation",
        "Checks for understanding",
    ),
    "Education Methodology": (
        "Pedagogical reasoning",
        "Assessment and differentiated instruction",
        "Evidence of learner progress",
    ),
    "Learner/Parent Scenarios": (
        "Empathy and professional communication",
        "Inclusive problem-solving",
        "Appropriate safeguarding and escalation",
    ),
    "Legal Screening": (
        "Relevant legal fundamentals",
        "Accuracy, confidentiality, and professional judgment",
    ),
    "Case Analysis": (
        "Issue identification and applicable rules",
        "Balanced analysis of facts and uncertainty",
        "Clear, well-supported conclusion",
    ),
    "Ethics/Client Scenarios": (
        "Professional responsibility and confidentiality",
        "Client communication and expectation setting",
        "Ethical escalation",
    ),
    "Service Screening": (
        "Service standards and role fundamentals",
        "Professionalism and attention to detail",
    ),
    "Customer Service Scenarios": (
        "Empathy and needs assessment",
        "Service recovery and de-escalation",
        "Clear resolution and follow-through",
    ),
    "Hospitality Operations": (
        "Operational prioritization",
        "Safety, quality, and guest experience",
        "Team coordination",
    ),
    "HR Screening": (
        "Employment and people-practice fundamentals",
        "Confidentiality and fair process",
    ),
    "People/Employee Scenarios": (
        "Empathetic employee communication",
        "Fair, consistent policy application",
        "Appropriate escalation and documentation",
    ),
    "Case Management Screening": (
        "Needs assessment and strengths-based practice",
        "Confidentiality and professional boundaries",
    ),
    "Client/Community Scenarios": (
        "Trauma-informed, culturally responsive communication",
        "Resource coordination and advocacy",
        "Safety and escalation",
    ),
    "Ethics/Safeguarding": (
        "Safeguarding and duty-of-care judgment",
        "Confidentiality and ethical boundaries",
        "Timely escalation and documentation",
    ),
    "Construction/Trade Screening": (
        "Role-specific practical knowledge",
        "Tools, materials, and standards",
        "Safe work practices",
    ),
    "Project/Site Scenario": (
        "Planning and sequencing",
        "Coordination under site constraints",
        "Risk response and communication",
    ),
    "Safety & Quality": (
        "Hazard recognition and controls",
        "Quality standards and inspection",
        "Stop-work and incident escalation",
    ),
    "Research Methods": (
        "Research question and methodology",
        "Evidence quality and limitations",
        "Ethical handling of research",
    ),
    "Experimental/Analytical Design": (
        "Study or experiment design",
        "Data analysis and reproducibility",
        "Interpretation of uncertainty",
    ),
    "Technical/Domain Review": (
        "Depth in the relevant scientific domain",
        "Clear explanation of methods and findings",
        "Limitations and future work",
    ),
}


def get_candidate_experience_level(
    employment_status: str | None,
    years_of_experience: float | None = None,
    current_role: str | None = None,
) -> str:
    if (
        (years_of_experience is not None and years_of_experience > 0)
        or employment_status == "employed"
        or (
            employment_status in {"unemployed", "career_changer"}
            and bool(current_role and current_role.strip())
        )
    ):
        return "experienced"
    if employment_status in {
        "school_student",
        "college_student",
        "recent_graduate",
    }:
        return "fresher"
    return "general"


def get_rounds_for_role(
    role_category: str,
    job_description: str | None = None,
    company_industry: str | None = None,
    *,
    candidate_level: str | None = None,
) -> Sequence[str]:
    role_text = role_category.casefold()
    rounds: Sequence[str] | None = None
    for domain, terms in DOMAIN_TERMS.items():
        if _contains_domain_term(role_text, terms):
            rounds = ROUND_SEQUENCES[domain]
            break
    if rounds is None and _contains_domain_term(role_text, TECHNICAL_ROLE_TERMS):
        rounds = ROUND_SEQUENCES["technology"]

    if rounds is None:
        description_text = (job_description or "").casefold()
        for domain, terms in DOMAIN_TERMS.items():
            if _contains_domain_term(description_text, terms):
                rounds = ROUND_SEQUENCES[domain]
                break
    if rounds is None:
        industry_text = (company_industry or "").casefold()
        for domain, terms in DOMAIN_TERMS.items():
            if _contains_domain_term(industry_text, terms):
                rounds = ROUND_SEQUENCES[domain]
                break
    if rounds is None:
        rounds = ROUND_SEQUENCES["technology"]

    if candidate_level == "fresher":
        return tuple(
            round_name
            for round_name in rounds
            if round_name not in FRESHER_INAPPROPRIATE_ROUNDS
        )
    return rounds


def get_first_round(
    role_category: str,
    difficulty_level: int,
    job_description: str | None = None,
    company_industry: str | None = None,
    *,
    candidate_level: str | None = None,
) -> str:
    del difficulty_level
    return get_rounds_for_role(
        role_category,
        job_description,
        company_industry,
        candidate_level=candidate_level,
    )[0]


def get_round_config(round_name: str) -> dict:
    return {
        "min_questions": 2,
        "max_questions": 20,
        "evaluation_criteria": list(
            ROUND_CRITERIA.get(
                round_name,
                ("Role-relevant knowledge", "Reasoning", "Clear communication"),
            )
        ),
    }


def get_next_round(
    current_round: str,
    role_category: str,
    difficulty_level: int,
    job_description: str | None = None,
    company_industry: str | None = None,
    *,
    candidate_level: str | None = None,
    planned_rounds: Sequence[str] | None = None,
) -> str | None:
    del difficulty_level
    rounds = planned_rounds or get_rounds_for_role(
        role_category,
        job_description,
        company_industry,
        candidate_level=candidate_level,
    )
    try:
        current_index = rounds.index(current_round)
    except ValueError:
        return None
    next_index = current_index + 1
    return rounds[next_index] if next_index < len(rounds) else None


def should_proceed_to_next_round(score: float, round_name: str) -> bool:
    del round_name
    return score >= 6
