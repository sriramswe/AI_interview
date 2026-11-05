from io import BytesIO
import pdfplumber
import re
from collections import Counter
from typing import Any

# Comprehensive skill dictionary to scan for in resumes
TECH_SKILLS_DATABASE = [
    # Languages
    "python", "java", "javascript", "typescript", "c++", "c#", "golang", "go",
    "ruby", "rust", "php", "swift", "kotlin", "scala", "r", "dart", "html", "css",
    # Frontend
    "react", "react.js", "next.js", "vue", "vue.js", "angular", "svelte",
    "tailwind css", "tailwind", "html5", "css3", "redux", "zustand", "graphql", "webpack", "vite",
    # Backend & Frameworks
    "fastapi", "flask", "django", "express", "express.js", "node.js", "nodejs", "nestjs",
    "spring boot", "asp.net", "laravel", "ruby on rails", "rest api", "restful api", "grpc", "microservices",
    # Databases & Storage
    "sql", "mysql", "postgresql", "postgres", "mongodb", "redis", "elasticsearch",
    "sqlite", "dynamodb", "cassandra", "supabase", "firebase", "prisma", "sqlalchemy",
    # Cloud & DevOps
    "docker", "kubernetes", "aws", "azure", "gcp", "google cloud", "ci/cd", "ci cd",
    "jenkins", "github actions", "terraform", "ansible", "linux", "nginx", "serverless",
    # AI / ML / Data
    "machine learning", "deep learning", "nlp", "computer vision", "llm", "genai", "generative ai",
    "pandas", "numpy", "scikit-learn", "tensorflow", "pytorch", "hugging face",
    "langchain", "vector database", "rag", "data science", "data analysis",
    # Tools & Methodologies
    "git", "github", "gitlab", "jira", "agile", "scrum", "system design",
    "unit testing", "pytest", "jest", "cypress", "postman"
]

COMMON_ACTION_VERBS = [
    "accelerated", "achieved", "analyzed", "architected", "automated", "built",
    "collaborated", "created", "decreased", "delivered", "deployed", "designed",
    "developed", "engineered", "established", "executed", "expanded", "generated",
    "implemented", "improved", "increased", "integrated", "launched", "led",
    "managed", "mentored", "maximized", "minimized", "modeled", "optimized",
    "orchestrated", "overhauled", "produced", "reduced", "refactored", "resolved",
    "restructured", "scaled", "simplified", "spearheaded", "streamlined", "transformed"
]

ATS_STOP_WORDS = {
    "about", "across", "after", "all", "also", "and", "any", "are", "as", "at",
    "be", "because", "been", "before", "being", "both", "but", "by", "can",
    "candidate", "could", "day", "demonstrated", "department", "develop",
    "different", "do", "each", "either", "experience", "for", "from", "good",
    "great", "have", "having", "how", "in", "including", "into", "is", "it",
    "its", "job", "knowledge", "may", "more", "most", "must", "new", "not",
    "of", "on", "or", "our", "other", "out", "over", "per", "please", "role",
    "required", "requirements", "should", "skill", "skills", "some", "such", "than", "that", "the", "their",
    "them", "then", "there", "these", "they", "this", "those", "through", "to",
    "under", "use", "using", "various", "very", "want", "was", "we", "well",
    "were", "what", "when", "where", "which", "who", "will", "with", "work",
    "you", "your",
}


def parse_resume_skills(file_path: str) -> list[str]:
    """
    Extracts text from an uploaded PDF resume and matches it against 
    known technical keywords to personalize interview questions.
    """
    extracted_text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                extracted_text += text + "\n"

    return find_resume_skills(extracted_text)


def parse_resume_skills_from_bytes(file_content: bytes) -> list[str]:
    with pdfplumber.open(BytesIO(file_content)) as pdf:
        extracted_text = "\n".join(
            text
            for page in pdf.pages
            if (text := page.extract_text())
        )
    return find_resume_skills(extracted_text)


def find_resume_skills(extracted_text: str) -> list[str]:
    lower_text = extracted_text.lower()
    found_skills = [
        skill for skill in set(TECH_SKILLS_DATABASE)
        if re.search(r'(?<![a-z0-9])' + re.escape(skill) + r'(?![a-z0-9])', lower_text)
    ]
    return sorted(found_skills, key=lambda s: (-len(s), s))


def analyze_resume_interview_context(resume_text: str) -> dict[str, Any]:
    skills = find_resume_skills(resume_text)
    highlights = [
        re.sub(r"\s+", " ", line).strip(" •\t")
        for line in resume_text.splitlines()
        if 45 <= len(line.strip()) <= 240
    ][:5]
    return {
        "summary": (
            f"Resume text extracted successfully. Found {len(skills)} recognized "
            f"technical skill{'' if len(skills) == 1 else 's'}."
        ),
        "strengths": skills,
        "skills": skills,
        "experience_highlights": highlights,
        "areas_to_probe": skills[:5],
    }


def chunk_resume_context(
    resume_text: str, *, chunk_size: int = 1000, max_chunks: int = 6
) -> str:
    chunks = []
    current_chunk = ""
    for line in resume_text.splitlines():
        words = re.findall(rf"\S{{1,{chunk_size}}}", line)
        for word in words:
            if current_chunk and len(current_chunk) + len(word) + 1 > chunk_size:
                chunks.append(current_chunk)
                current_chunk = ""
                if len(chunks) >= max_chunks:
                    return "\n\n".join(chunks)
            current_chunk = f"{current_chunk} {word}".strip()
    if current_chunk and len(chunks) < max_chunks:
        chunks.append(current_chunk)
    return "\n\n".join(chunks)


def analyze_resume_match(
    resume_text: str, job_description: str | None
) -> dict[str, int | list[str] | None]:
    if not job_description or not job_description.strip():
        return {
            "ats_score": None,
            "matched_keywords": [],
            "missing_keywords": [],
            "suggestions": ["Add a job description to calculate keyword alignment."],
        }

    job_text = job_description.casefold()
    resume_text_normalized = resume_text.casefold()
    skill_terms = sorted(
        set(TECH_SKILLS_DATABASE),
        key=lambda term: (-len(term), term),
    )
    keywords = [
        term
        for term in skill_terms
        if re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", job_text)
    ]

    raw_words = [
        re.sub(r'^[^\w+#]+|[^\w+#]+$', '', w)
        for w in re.findall(r"[a-z0-9+#.-]{2,}", job_text)
    ]
    word_counts = Counter(
        w for w in raw_words
        if len(w) >= 3 and w not in ATS_STOP_WORDS and not w.isdigit()
    )
    for word, _ in word_counts.most_common(25):
        if word not in keywords:
            keywords.append(word)

    matched = [
        keyword
        for keyword in keywords
        if re.search(
            r"(?<![a-z0-9])" + re.escape(keyword) + r"(?![a-z0-9])",
            resume_text_normalized,
        )
    ]
    missing = [keyword for keyword in keywords if keyword not in matched]
    score = round((len(matched) / len(keywords)) * 100) if keywords else 0
    suggestions = [
        f"Add relevant evidence for '{keyword}' if it reflects your experience."
        for keyword in missing[:5]
    ]
    if not keywords:
        suggestions.append(
            "The job description did not contain enough recognizable keywords to score."
        )

    return {
        "ats_score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "suggestions": suggestions,
    }


def calculate_detailed_ats_score(
    resume_text: str,
    job_description: str | None = None,
    target_role: str | None = None,
) -> dict[str, Any]:
    """
    Comprehensive ATS score check comparing a resume to a job description or role.
    Computes keyword matching, structure, contact info, action verbs, and quantifiable metrics.
    """
    resume_norm = resume_text.strip()
    resume_lower = resume_norm.lower()

    # 1. Contact Information Audit
    has_email = bool(re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', resume_norm))
    has_phone = bool(re.search(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', resume_norm))
    has_linkedin = bool(re.search(r'linkedin\.com/in/[a-zA-Z0-9_-]+', resume_lower))
    has_github = bool(re.search(r'github\.com/[a-zA-Z0-9_-]+', resume_lower))

    # 2. Section Headings Check
    sections = {
        "Summary / Objective": bool(re.search(r'\b(summary|objective|profile|about me)\b', resume_lower)),
        "Work Experience": bool(re.search(r'\b(experience|employment|work history|professional background)\b', resume_lower)),
        "Education": bool(re.search(r'\b(education|academic|degree|university|college|bachelor|master|b\.tech|m\.tech|b\.s|m\.s)\b', resume_lower)),
        "Skills": bool(re.search(r'\b(skills|technical skills|technologies|proficiencies|competencies)\b', resume_lower)),
        "Projects": bool(re.search(r'\b(projects|personal projects|portfolio|key achievements)\b', resume_lower)),
        "Certifications": bool(re.search(r'\b(certifications|certificates|licenses|courses)\b', resume_lower)),
    }
    present_sections = [sec for sec, present in sections.items() if present]
    missing_sections = [sec for sec, present in sections.items() if not present]
    section_score = round((len(present_sections) / len(sections)) * 100)

    # 3. Measurable Impact & Numbers Detection (quantifiable achievements)
    metrics_matches = re.findall(
        r'(\b\d+(\.\d+)?%\b|\$\d+([kKmMbB])?|\b\d+[kKmMbB]\b|\b\d+x\b|\b\d+\+\s*(users|clients|customers|requests|queries|rps|tps|projects|teams|engineers|members|ms|seconds|minutes|hours)\b)',
        resume_norm,
        flags=re.IGNORECASE,
    )
    metrics_count = len(metrics_matches)
    metrics_score = min(100, round((metrics_count / 5) * 100))

    # 4. Action Verbs Audit
    found_action_verbs = [
        verb for verb in COMMON_ACTION_VERBS
        if re.search(r'\b' + re.escape(verb) + r'\b', resume_lower)
    ]
    action_verb_count = len(found_action_verbs)
    action_score = min(100, round((action_verb_count / 8) * 100))

    # 5. Detected Technical Skills
    detected_skills = find_resume_skills(resume_norm)

    # 6. Keyword Match against Job Description or Role
    effective_jd = (job_description or "").strip()
    if not effective_jd and target_role:
        effective_jd = f"{target_role} software development engineering proficiency with modern web frameworks, databases, and APIs."

    match_analysis = analyze_resume_match(resume_norm, effective_jd)
    keyword_score = match_analysis["ats_score"] if match_analysis["ats_score"] is not None else 65
    matched_keywords = match_analysis.get("matched_keywords", [])
    missing_keywords = match_analysis.get("missing_keywords", [])

    # 7. Formatting & Readability Score
    word_count = len(resume_norm.split())
    bullet_count = len(re.findall(r'^[•\-\*]\s+', resume_norm, flags=re.MULTILINE))
    
    formatting_issues = []
    if word_count < 200:
        formatting_issues.append("Resume appears too short (under 200 words). Add detail to experience and projects.")
    elif word_count > 1200:
        formatting_issues.append("Resume exceeds 1,200 words. Consider condensing to 1-2 pages for ATS readability.")
    if not has_email:
        formatting_issues.append("No professional email address detected.")
    if not has_phone:
        formatting_issues.append("No phone number detected.")
    
    format_base = 100 - (len(formatting_issues) * 15)
    format_score = max(20, min(100, format_base))

    # 8. Overall Weighted ATS Score (out of 100)
    # Weights: Keyword alignment 40%, Section completeness 20%, Quantifiable metrics 20%, Action verbs 10%, Formatting 10%
    overall_ats_score = round(
        (keyword_score * 0.40) +
        (section_score * 0.20) +
        (metrics_score * 0.20) +
        (action_score * 0.10) +
        (format_score * 0.10)
    )
    overall_ats_score = max(5, min(98, overall_ats_score))

    # 9. Grade Determination
    if overall_ats_score >= 85:
        grade = "Strong Match"
        status_color = "emerald"
        verdict = "Your resume has high ATS compatibility and should pass initial applicant tracking systems."
    elif overall_ats_score >= 70:
        grade = "Competitive"
        status_color = "blue"
        verdict = "Solid resume foundation. Incorporating the missing keywords and metrics will boost your ranking."
    elif overall_ats_score >= 50:
        grade = "Moderate Match"
        status_color = "amber"
        verdict = "Needs refinement. Several core job keywords or quantifiable achievements are missing."
    else:
        grade = "Low Match"
        status_color = "rose"
        verdict = "Significant gaps identified. Update your skills and project bullets to match the target job description."

    # 10. Curated Actionable Suggestions
    suggestions = []
    if missing_keywords:
        top_missing = missing_keywords[:6]
        suggestions.append(f"Add key target terms: {', '.join(top_missing)} in your skills or project bullets.")
    if metrics_count < 3:
        suggestions.append("Add quantifiable metrics (e.g., 'reduced latency by 35%', 'handled 50k+ daily users').")
    if not sections.get("Summary / Objective"):
        suggestions.append("Include a 2-3 line Professional Summary at the top emphasizing your target role.")
    if not sections.get("Projects"):
        suggestions.append("Add a dedicated Projects section showcasing hands-on implementations.")
    if not has_linkedin or not has_github:
        suggestions.append("Include links to your LinkedIn profile and GitHub portfolio.")
    for issue in formatting_issues:
        if issue not in suggestions:
            suggestions.append(issue)

    return {
        "ats_score": overall_ats_score,
        "score_grade": grade,
        "status_color": status_color,
        "verdict": verdict,
        "word_count": word_count,
        "breakdown": {
            "keyword_match": keyword_score,
            "section_completeness": section_score,
            "measurable_metrics": metrics_score,
            "action_verbs": action_score,
            "formatting_readability": format_score,
        },
        "matched_keywords": matched_keywords,
        "missing_keywords": missing_keywords,
        "detected_skills": detected_skills,
        "contact_info": {
            "email_found": has_email,
            "phone_found": has_phone,
            "linkedin_found": has_linkedin,
            "github_found": has_github,
        },
        "sections": {
            "present": present_sections,
            "missing": missing_sections,
        },
        "metrics_found_count": metrics_count,
        "action_verbs_found": found_action_verbs[:10],
        "suggestions": suggestions,
    }
