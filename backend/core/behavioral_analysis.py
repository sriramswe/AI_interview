import re


_WORD_PATTERN = re.compile(r"\b[\w']+\b")
_FILLER_PATTERN = re.compile(r"\b(?:um+|uh+|er+|ah+|like)\b", re.IGNORECASE)


def analyze_speaking_metrics(
    answer: str, duration_seconds: float | None = None
) -> dict[str, int | float | str | None]:
    words = _WORD_PATTERN.findall(answer)
    fillers = _FILLER_PATTERN.findall(answer)
    word_count = len(words)
    words_per_minute = (
        round(word_count * 60 / duration_seconds, 1)
        if duration_seconds is not None and duration_seconds > 0
        else None
    )
    if words_per_minute is None:
        pace = None
    elif words_per_minute < 100:
        pace = "slow"
    elif words_per_minute <= 160:
        pace = "typical"
    else:
        pace = "fast"

    return {
        "word_count": word_count,
        "filler_word_count": len(fillers),
        "filler_rate_per_100_words": (
            round(len(fillers) * 100 / word_count, 1) if word_count else 0.0
        ),
        "duration_seconds": duration_seconds,
        "words_per_minute": words_per_minute,
        "speaking_pace": pace,
    }
