import logging
import os
import re
from functools import lru_cache

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _get_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("SENTENCE_TRANSFORMER_MODEL", "all-MiniLM-L6-v2")
        return SentenceTransformer(model_name)
    except Exception:
        logger.warning(
            "Sentence Transformer model could not be loaded; using TF-IDF similarity.",
            exc_info=True,
        )
        return None


def encode_semantic_text(text):
    """Encode text with the shared sentence model for semantic vector storage."""
    if not text.strip():
        raise ValueError("Text to embed cannot be blank.")
    model = _get_sentence_transformer()
    if model is None:
        raise RuntimeError(
            "The sentence embedding model is unavailable; semantic search cannot run."
        )
    return model.encode([text], normalize_embeddings=True)[0].tolist()


def preprocess_text(text):
    """
    Preprocess the input text by converting to lowercase, removing punctuation, and stripping whitespace.
    """
    text = text.lower() 
    text = re.sub(r'[^\w\s]', '', text) 
    text = text.strip()
    return text

def compute_semantic_similarity(user_answer, reference_answer):
    """Compute semantic closeness between user answer and reference answer (0 to 100)."""
    if not user_answer.strip() or not reference_answer.strip():
        return 0.0
    sentence_transformer_model = _get_sentence_transformer()
    if sentence_transformer_model is not None:
        user_embedding = sentence_transformer_model.encode([user_answer])
        reference_embedding = sentence_transformer_model.encode([reference_answer])
        similarity = cosine_similarity(user_embedding, reference_embedding)[0][0]
        score = float(similarity) * 100
    else:
        vectorizer = TfidfVectorizer()
        try:
            tfidf_matrix = vectorizer.fit_transform([user_answer, reference_answer])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            score = float(similarity) * 100
        except ValueError:
            score = 0.0
    return max(0.0, min(100.0, score))

def evaluate_keywords(user_text, key_concepts):
    """Check how many key concept keywords are present in user text."""
    if isinstance(key_concepts, str):
        key_concepts = [concept.strip() for concept in key_concepts.split(",") if concept.strip()]
    else:
        key_concepts = list(key_concepts or [])
    if not key_concepts:
        return 100.0, []

    user_text_clean = preprocess_text(user_text)
    matched = []
    missing = []

    for concept in key_concepts:
        concept_clean = preprocess_text(concept)
        if concept_clean in user_text_clean:
            matched.append(concept)
        else:
            missing.append(concept)

    coverage_score = (len(matched) / len(key_concepts)) * 100
    return round(coverage_score, 2), missing

def evaluate_answer(user_answer, reference_answer, key_concepts):
    """
    Hybrid scoring algorithm combining:
    - 60% Semantic Similarity (Sentence Transformers / TF-IDF)
    - 40% Keyword Concept Coverage
    """
    clean_user = preprocess_text(user_answer)
    clean_ref = preprocess_text(reference_answer)
    if isinstance(key_concepts, str):
        key_concepts = [concept.strip() for concept in key_concepts.split(",") if concept.strip()]
    else:
        key_concepts = list(key_concepts or [])

    # Short/empty answer penalty
    if len(clean_user.split()) < 3:
        return {
            "similarity_score": 0.0,
            "keyword_score": 0.0,
            "final_score": 0.0,
            "missing_concepts": key_concepts,
            "feedback": "Answer is too brief. Please provide a more detailed explanation covering core technical concepts."
        }

    similarity_score = compute_semantic_similarity(clean_user, clean_ref)
    keyword_score, missing_concepts = evaluate_keywords(user_answer, key_concepts)

    final_score = (0.60 * similarity_score) + (0.40 * keyword_score)
    final_score = round(final_score, 2)

    # Generate actionable feedback based on score range
    if final_score >= 80:
        feedback = "Excellent response! You clearly covered the core domain concepts and explained them effectively."
    elif final_score >= 50:
        feedback = f"Good attempt. To reach an expert level, try explicitly addressing missing concepts: {', '.join(missing_concepts)}."
    else:
        feedback = f"Needs improvement. Focus on incorporating key topics like: {', '.join(missing_concepts)}."

    return {
        "similarity_score": round(similarity_score, 2),
        "keyword_score": round(keyword_score, 2),
        "final_score": final_score,
        "missing_concepts": missing_concepts,
        "feedback": feedback
    }