from core.database import SessionLocal, engine, Base
from core.models import Question

Base.metadata.create_all(bind=engine)

SEED_QUESTIONS = [
    {
        "role": "Python Developer",
        "category": "Technical",
        "difficulty": "Beginner",
        "question_text": "What is the difference between list and tuple in Python?",
        "reference_answer": "Lists are mutable and defined with square brackets, allowing items to be added or altered. Tuples are immutable and defined with parentheses, making them faster and memory efficient.",
        "key_concepts": "mutability, immutability, memory, indexing, performance"
    },
    {
        "role": "Python Developer",
        "category": "Technical",
        "difficulty": "Intermediate",
        "question_text": "How does Python's GIL (Global Interpreter Lock) affect multi-threading?",
        "reference_answer": "The GIL is a mutex that prevents multiple native threads from executing Python bytecodes at once. This limits CPU-bound multi-threading, while I/O-bound tasks still benefit from concurrency.",
        "key_concepts": "GIL, mutex, multi-threading, CPU-bound, I/O-bound, concurrency"
    },
    {
        "role": "Data Scientist",
        "category": "Technical",
        "difficulty": "Intermediate",
        "question_text": "Explain the bias-variance tradeoff in machine learning.",
        "reference_answer": "Bias is error caused by overly simplistic model assumptions, leading to underfitting. Variance is error caused by excessive sensitivity to training data fluctuations, leading to overfitting. The goal is to minimize total error by finding a balanced sweet spot.",
        "key_concepts": "bias, variance, overfitting, underfitting, generalization error"
    },
    {
        "role": "Software Engineer",
        "category": "HR",
        "difficulty": "Beginner",
        "question_text": "Tell me about a time you had a technical disagreement with a colleague and how you resolved it.",
        "reference_answer": "I listened to their perspective, evaluated both technical architectures against concrete project constraints, created a quick benchmark prototype, and reached a consensus aligned with project timelines.",
        "key_concepts": "collaboration, consensus, benchmarking, active listening, communication"
    }
]

def run_seed():
    db = SessionLocal()
    try:
        for item in SEED_QUESTIONS:
            existing = db.query(Question).filter_by(
                question_text=item["question_text"]
            ).first()
            if not existing:
                db.add(Question(**item))
        db.commit()
        print("Question bank seeded successfully.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_seed()