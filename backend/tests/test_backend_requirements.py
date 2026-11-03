import os
import unittest
from unittest.mock import patch


os.environ.setdefault(
    "MYSQL_URL",
    "mysql+pymysql://root:test-password@127.0.0.1:3306/interviewai_test?charset=utf8mb4",
)
os.environ["JWT_SECRET_KEY"] = "backend-tests-only-secret-0123456789"

from fastapi.testclient import TestClient
from sqlalchemy import delete

import app as backend_app
from core.database import SessionLocal
from core.models import (
    DevelopmentWorkflow,
    InterviewSession,
    PaymentSubmission,
    Question,
    RevokedToken,
    Subscription,
    User,
    UserAnswer,
)


class BackendRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.client_context = TestClient(backend_app.app)
        self.client = self.client_context.__enter__()
        with SessionLocal() as db:
            db.execute(delete(UserAnswer))
            db.execute(delete(InterviewSession))
            db.execute(delete(DevelopmentWorkflow))
            db.execute(delete(PaymentSubmission))
            db.execute(delete(Subscription))
            db.execute(delete(RevokedToken))
            db.execute(delete(Question))
            db.execute(delete(User))
            db.commit()

    def tearDown(self):
        self.client_context.__exit__(None, None, None)

    def _register(self, email="student@example.com"):
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "Student",
                "email": email,
                "password": "secure-password-123",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    def test_profile_management_and_logout_revoke_token(self):
        headers = self._register()
        profile = self.client.get("/api/users/me", headers=headers)
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.json()["username"], "Student")

        updated = self.client.patch(
            "/api/users/me",
            headers=headers,
            json={"username": "Updated Student"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)
        self.assertEqual(updated.json()["username"], "Updated Student")

        logout = self.client.post("/api/auth/logout", headers=headers)
        self.assertEqual(logout.status_code, 204, logout.text)
        rejected = self.client.get("/api/users/me", headers=headers)
        self.assertEqual(rejected.status_code, 401)

    def test_question_practice_retry_feedback_and_history(self):
        role = "Backend Test Engineer"
        with SessionLocal() as db:
            questions = [
                Question(
                    role=role,
                    category="Technical",
                    difficulty="Beginner",
                    question_text="Explain list mutability.",
                    reference_answer="Lists are mutable ordered collections.",
                    key_concepts="mutable, ordered, collection",
                ),
                Question(
                    role=role,
                    category="Technical",
                    difficulty="Beginner",
                    question_text="Explain tuple immutability.",
                    reference_answer="Tuples are immutable ordered collections.",
                    key_concepts="immutable, ordered, collection",
                ),
            ]
            db.add_all(questions)
            db.commit()
            first_question_id, second_question_id = [
                question.id for question in questions
            ]

        headers = self._register()
        started = self.client.post(
            "/api/practice/start",
            headers=headers,
            json={
                "role": role,
                "difficulty": "Beginner",
                "category": "Technical",
            },
        )
        self.assertEqual(started.status_code, 201, started.text)
        interview_id = started.json()["interview_id"]

        nlp_result = {
            "similarity_score": 80.0,
            "keyword_score": 66.67,
            "final_score": 74.67,
            "missing_concepts": ["collection"],
            "feedback": "Add the missing concept.",
        }
        with patch.object(backend_app, "evaluate_answer_nlp", return_value=nlp_result):
            first = self.client.post(
                "/api/practice/answer",
                headers=headers,
                json={
                    "interview_id": interview_id,
                    "answer": "Lists are mutable and ordered.",
                },
            )
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(first.json()["reference_answer"], "Lists are mutable ordered collections.")
            self.assertEqual(first.json()["next_question"]["id"], second_question_id)

            retry = self.client.post(
                "/api/practice/answer",
                headers=headers,
                json={
                    "interview_id": interview_id,
                    "question_id": first_question_id,
                    "answer": "Lists are mutable ordered collections.",
                },
            )
            self.assertEqual(retry.status_code, 200, retry.text)
            self.assertTrue(retry.json()["retry"])
            self.assertEqual(retry.json()["next_question"]["id"], second_question_id)

            final = self.client.post(
                "/api/practice/answer",
                headers=headers,
                json={
                    "interview_id": interview_id,
                    "answer": "Tuples are immutable ordered collections.",
                },
            )
            self.assertEqual(final.status_code, 200, final.text)
            self.assertTrue(final.json()["session_completed"])

        history = self.client.get(
            f"/api/interviews/history/{interview_id}", headers=headers
        )
        self.assertEqual(history.status_code, 200, history.text)
        self.assertEqual(len(history.json()["answers"]), 3)
        self.assertEqual(
            history.json()["answers"][0]["reference_answer"],
            "Lists are mutable ordered collections.",
        )
        self.assertEqual(history.json()["total_questions"], 3)
        self.assertEqual(history.json()["session_id"], interview_id)
        self.assertEqual(history.json()["interview_round"], "Question Practice")
        self.assertIn("interviewer_name", history.json())
        self.assertIn("is_panel", history.json())

        history_list = self.client.get("/api/interviews/history", headers=headers)
        self.assertEqual(history_list.status_code, 200, history_list.text)
        self.assertEqual(history_list.json()[0]["session_id"], interview_id)
        self.assertIn("round_scores", history_list.json()[0])
        self.assertIn("rounds_completed", history_list.json()[0])

        second_user_headers = self._register("another@example.com")
        denied_history = self.client.get(
            f"/api/interviews/history/{interview_id}",
            headers=second_user_headers,
        )
        self.assertEqual(denied_history.status_code, 404)

    def test_resume_parse_requires_authentication_and_rejects_non_pdf(self):
        unauthorized = self.client.post(
            "/api/resume/parse",
            files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
        )
        self.assertEqual(unauthorized.status_code, 401)

        headers = self._register()
        invalid_pdf = self.client.post(
            "/api/resume/parse",
            headers=headers,
            files={"file": ("resume.pdf", b"not a PDF", "application/pdf")},
        )
        self.assertEqual(invalid_pdf.status_code, 400)

if __name__ == "__main__":
    unittest.main()
