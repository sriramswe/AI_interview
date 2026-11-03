import os
import unittest
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from unittest.mock import patch

os.environ.setdefault(
    "MYSQL_URL",
    "mysql+pymysql://root:root@127.0.0.1:3306/interviewai_test?charset=utf8mb4",
)
os.environ["JWT_SECRET_KEY"] = "backend-tests-only-secret-0123456789"

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.mysql import MEDIUMBLOB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app as backend_app
from core import database
from core.models import Subscription, User
from services.billing import PLAN_PRICES_RUPEES
from services.resume_builder import RESUME_TEMPLATES


@compiles(MEDIUMBLOB, "sqlite")
def compile_mediumblob_for_sqlite(_type, _compiler, **_kwargs):
    return "BLOB"


class ResumeBuilderTests(unittest.TestCase):
    def setUp(self):
        self.original_engine = database.engine
        self.original_session_factory = database.SessionLocal
        self.test_engine = create_engine(
            "sqlite+pysqlite://",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        database.engine = self.test_engine
        database.SessionLocal = sessionmaker(
            bind=self.test_engine,
            autoflush=False,
            expire_on_commit=False,
        )
        self.client_context = TestClient(backend_app.app)
        self.client = self.client_context.__enter__()
        self.email = f"resume-{uuid4().hex}@example.com"
        response = self.client.post(
            "/api/auth/register",
            json={
                "username": "Resume Tester",
                "email": self.email,
                "password": "secure-password-123",
            },
        )
        self.assertEqual(response.status_code, 201, response.text)
        self.headers = {
            "Authorization": f"Bearer {response.json()['access_token']}"
        }

    def tearDown(self):
        self.client_context.__exit__(None, None, None)
        database.engine = self.original_engine
        database.SessionLocal = self.original_session_factory
        self.test_engine.dispose()

    def _create_resume(self, template_id="classic-navy", source="template"):
        return self.client.post(
            "/api/resumes",
            headers=self.headers,
            json={
                "template_id": template_id,
                "title": "Software Engineer",
                "source": source,
                "content": {
                    "full_name": "Resume Tester",
                    "headline": "Software Engineer",
                    "skills": ["Python", "React"],
                },
            },
        )

    def _activate_plan(self, plan):
        with database.SessionLocal() as db:
            user = db.scalar(
                select(User).where(User.email == self.email)
            )
            db.add(
                Subscription(
                    user_id=user.id,
                    plan=plan,
                    status="active",
                    started_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                )
            )
            db.commit()

    def test_catalog_contains_thirty_templates_and_only_available_plan_prices(self):
        response = self.client.get("/api/resumes/templates")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 30)
        self.assertEqual(len({item["id"] for item in response.json()}), 30)
        self.assertEqual(PLAN_PRICES_RUPEES, {"pro": 299, "elite": 599})

    def test_removed_plan_cannot_be_checked_out(self):
        response = self.client.post(
            "/api/billing/checkout",
            headers=self.headers,
            json={"plan": "pre"},
        )
        self.assertEqual(response.status_code, 422)

    def test_free_plan_can_build_three_and_is_blocked_on_fourth(self):
        for _ in range(3):
            response = self._create_resume()
            self.assertEqual(response.status_code, 201, response.text)
        blocked = self._create_resume()
        self.assertEqual(blocked.status_code, 403)
        self.assertIn("all 3 free resume builds", blocked.json()["detail"])

        usage = self.client.get("/api/resumes", headers=self.headers)
        self.assertEqual(usage.status_code, 200)
        self.assertEqual(usage.json()["build_count"], 3)
        self.assertEqual(usage.json()["remaining_free_builds"], 0)
        self.assertFalse(usage.json()["can_build"])

    def test_legacy_resume_plan_keeps_existing_access_until_expiry(self):
        self._activate_plan("pre")
        for _ in range(4):
            response = self._create_resume()
            self.assertEqual(response.status_code, 201, response.text)

        usage = self.client.get("/api/resumes", headers=self.headers)
        self.assertEqual(usage.json()["plan"], "legacy_resume")
        self.assertEqual(usage.json()["remaining_free_builds"], None)
        self.assertTrue(usage.json()["can_customize_upload"])

        subscription = self.client.get("/api/billing/subscription", headers=self.headers)
        self.assertEqual(subscription.json()["plan"], "legacy_resume")

        upload = self.client.post(
            "/api/resumes/import",
            headers=self.headers,
            files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
        )
        self.assertEqual(upload.status_code, 400)
        self.assertIn("valid PDF", upload.json()["detail"])

    def test_legacy_resume_plan_can_import_and_save_a_customized_resume(self):
        self._activate_plan("pre")
        with patch.object(
            backend_app, "_extract_resume_text", return_value="Candidate Name\nExperience"
        ):
            imported = self.client.post(
                "/api/resumes/import",
                headers=self.headers,
                files={"file": ("resume.pdf", b"%PDF-1.7", "application/pdf")},
            )
        self.assertEqual(imported.status_code, 200, imported.text)
        self.assertEqual(imported.json()["resume_text"], "Candidate Name\nExperience")

        created = self._create_resume(source="upload")
        self.assertEqual(created.status_code, 201, created.text)
        self.assertEqual(created.json()["source"], "upload")

    def test_existing_pro_plan_does_not_unlock_builder_uploads_or_unlimited_builds(self):
        self._activate_plan("pro")
        for _ in range(3):
            response = self._create_resume()
            self.assertEqual(response.status_code, 201, response.text)

        blocked = self._create_resume()
        self.assertEqual(blocked.status_code, 403)
        upload = self.client.post(
            "/api/resumes/import",
            headers=self.headers,
            files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
        )
        self.assertEqual(upload.status_code, 403, upload.text)

    def test_free_user_cannot_import_or_save_an_uploaded_resume(self):
        upload = self.client.post(
            "/api/resumes/import",
            headers=self.headers,
            files={"file": ("resume.pdf", b"not a pdf", "application/pdf")},
        )
        self.assertEqual(upload.status_code, 403)

        created = self._create_resume(source="upload")
        self.assertEqual(created.status_code, 403)


if __name__ == "__main__":
    unittest.main()
