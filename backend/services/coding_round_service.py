import math

from fastapi import HTTPException, status


PROBLEM_FIELDS = {
    "title": str,
    "statement": str,
    "examples": list,
    "constraints": list,
    "evaluation_bar": list,
    "starter_code": str,
    "function_signature": str,
    "resume_skill_targets": list,
}


def validate_problem(problem: dict) -> dict:
    for key, expected_type in PROBLEM_FIELDS.items():
        value = problem.get(key)
        if not isinstance(value, expected_type):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"The AI coding problem has an invalid {key} field.",
            )
    if not problem["title"].strip() or not problem["statement"].strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem is missing its title or statement.",
        )
    if len(problem["title"]) > 200 or len(problem["statement"]) > 8000:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem text exceeded its allowed size.",
        )
    if not 1 <= len(problem["examples"]) <= 5 or len(problem["constraints"]) > 20:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem has an invalid number of examples or constraints.",
        )
    if any(not isinstance(item, dict) for item in problem["examples"]):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem examples must be objects.",
        )
    for item in problem["examples"]:
        if any(not isinstance(item.get(key), str) for key in ("input", "output", "explanation")):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Each AI coding problem example must include input, output, and explanation text.",
            )
        if any(len(item[key]) > 2000 for key in ("input", "output", "explanation")):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="An AI coding problem example exceeded its allowed size.",
            )
    for key in ("constraints", "evaluation_bar"):
        if (
            len(problem[key]) > 20
            or any(not isinstance(item, str) or not item.strip() or len(item) > 2000 for item in problem[key])
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"The AI coding problem has an invalid {key} item.",
            )
    targets = problem["resume_skill_targets"]
    if len(targets) > 3 or any(
        not isinstance(item, str) or not item.strip() or len(item) > 300 for item in targets
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem has invalid resume skill targets.",
        )
    if not problem["starter_code"].strip() or len(problem["starter_code"]) > 12000:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding problem has invalid starter code.",
        )
    return problem


def normalize_judgement(judgement: dict, role: str, sub_role: str) -> dict:
    score_fields = ("correctness_score", "complexity_score", "quality_score")
    scores = {}
    for field in score_fields:
        raw = judgement.get(field)
        if isinstance(raw, bool):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI coding evaluation returned an invalid score.",
            )
        try:
            score = float(raw)
        except (OverflowError, TypeError, ValueError) as error:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI coding evaluation returned an invalid score.",
            ) from error
        if not math.isfinite(score) or not 0 <= score <= 100:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="AI coding scores must be between 0 and 100.",
            )
        scores[field] = round(score, 1)

    role_key = f"{role} {sub_role}".casefold()
    if any(term in role_key for term in ("genai", "generative ai", "llm", "rag")):
        weights = (0.55, 0.25, 0.20)
    elif any(term in role_key for term in ("ai", "ml", "machine learning", "data scientist")):
        weights = (0.60, 0.25, 0.15)
    else:
        weights = (0.65, 0.20, 0.15)
    total_score = round(
        scores["correctness_score"] * weights[0]
        + scores["complexity_score"] * weights[1]
        + scores["quality_score"] * weights[2],
        1,
    )

    text_fields = (
        "correctness_feedback",
        "complexity_feedback",
        "quality_feedback",
    )
    list_fields = ("dry_run_trace", "strengths", "improvements")
    if any(
        not isinstance(judgement.get(field), str)
        or not judgement[field].strip()
        or len(judgement[field]) > 5000
        for field in text_fields
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding evaluation returned incomplete feedback.",
        )
    if any(
        not isinstance(judgement.get(field), list)
        or len(judgement[field]) > 30
        or any(not isinstance(item, str) or len(item) > 2000 for item in judgement[field])
        for field in list_fields
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI coding evaluation returned an invalid feedback list.",
        )
    return {
        **scores,
        "total_score": total_score,
        "passed": total_score > 70,
        **{field: judgement[field] for field in text_fields + list_fields},
        "evaluation_notice": (
            "This is a static AI review and reasoning trace; the submitted code was not executed "
            "and no test suite was run."
        ),
    }


def validate_hint(payload: dict, tier: int) -> dict:
    hint = payload.get("hint")
    if not isinstance(hint, str) or not hint.strip():
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI hint response was empty or invalid.",
        )
    return {"tier": tier, "hint": hint.strip()}


def validate_roadmap(payload: dict) -> dict:
    days = payload.get("days")
    failed_topics = payload.get("failed_topics")
    resources = payload.get("resource_recommendations")
    if not isinstance(days, list) or len(days) != 7:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI learning roadmap must contain exactly seven days.",
        )
    if not isinstance(failed_topics, list) or not isinstance(resources, list):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI learning roadmap is missing its topic or resource lists.",
        )
    for index, day in enumerate(days, start=1):
        if (
            not isinstance(day, dict)
            or day.get("day") != index
            or not isinstance(day.get("focus"), str)
            or not day["focus"].strip()
            or not isinstance(day.get("activities"), list)
            or any(not isinstance(item, str) or not item.strip() for item in day["activities"])
            or not isinstance(day.get("practice_prompt"), str)
            or not day["practice_prompt"].strip()
        ):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="The AI learning roadmap has an invalid day entry.",
            )
    if any(
        not isinstance(item, str) or not item.strip()
        for item in failed_topics + resources
    ):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI learning roadmap topic or resource list is invalid.",
        )
    return payload
