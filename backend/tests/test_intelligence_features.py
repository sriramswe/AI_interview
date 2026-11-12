import asyncio
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from scripts.prune_discoveries import prune_discoveries
from services.intelligence_service import ProductionIntelligenceService


class IntelligenceFeatureTests(unittest.TestCase):
    def test_router_preserves_requested_region(self):
        service = ProductionIntelligenceService()
        state = {
            "company_name": "Acme",
            "industry": None,
            "geography": None,
            "requested_geography": "India",
            "job_description": None,
            "research_data": None,
            "is_synthetic": False,
            "confidence_score": 0,
            "generated_profile": None,
            "is_valid": False,
            "iterations": 0,
            "sources": [],
            "search_query": None,
            "audited_data": None,
            "audit_log": [],
            "critic_feedback": None,
            "error": None,
        }

        with patch(
            "services.intelligence_service.gemini_service._generate",
            new=AsyncMock(return_value=json.dumps({
                    "suggested_query": "Acme interview process",
                    "detected_industry": "Technology",
                    "detected_geography": "United States",
                })),
        ):
            result = asyncio.run(service.router_node(state))

        self.assertEqual(result["geography"], "India")
        self.assertIn("India", result["search_query"])

    def test_public_research_retries_transient_search_failures(self):
        service = ProductionIntelligenceService()
        attempts = []

        class FakeSearch:
            def __init__(self, timeout):
                self.timeout = timeout

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def text(self, query, max_results):
                attempts.append((query, max_results))
                if len(attempts) < 3:
                    raise RuntimeError("temporary network failure")
                return []

        state = {
            "company_name": "Acme",
            "geography": None,
            "search_query": "Acme interview process",
            "is_synthetic": False,
            "confidence_score": 0,
            "research_data": None,
            "sources": [],
        }
        with (
            patch("services.intelligence_service.DDGS", FakeSearch),
            patch("services.intelligence_service.time.sleep"),
        ):
            result = asyncio.run(service.researcher_node(state))

        self.assertEqual(len(attempts), 3)
        self.assertTrue(result["is_synthetic"])
        self.assertEqual(service.get_discovery_status("Acme")["mode"], "stealth")

    def test_repeated_critic_rejection_uses_generic_unverified_profile(self):
        service = ProductionIntelligenceService()
        state = {
            "company_name": "Wipro",
            "industry": None,
            "geography": "India",
            "requested_geography": "India",
            "job_description": None,
            "research_data": None,
            "is_synthetic": False,
            "confidence_score": 25,
            "generated_profile": {"interview_style": "Unsupported claim"},
            "is_valid": False,
            "iterations": 2,
            "sources": [],
            "search_query": None,
            "audited_data": None,
            "audit_log": [],
            "critic_feedback": "Company-specific claims are unverified.",
            "error": None,
        }

        async def pass_through(current_state):
            return current_state

        async def generate_unverified_profile(current_state):
            current_state["iterations"] += 1
            current_state["generated_profile"] = {"company_name": "Wipro"}
            return current_state

        async def reject_profile(current_state):
            current_state["is_valid"] = False
            current_state["critic_feedback"] = "Company-specific claims are unverified."
            return current_state

        with (
            patch.object(service, "router_node", new=AsyncMock(side_effect=pass_through)),
            patch.object(service, "researcher_node", new=AsyncMock(side_effect=pass_through)),
            patch.object(service, "auditor_node", new=AsyncMock(side_effect=pass_through)),
            patch.object(
                service,
                "architect_node",
                new=AsyncMock(side_effect=generate_unverified_profile),
            ),
            patch.object(service, "critic_node", new=AsyncMock(side_effect=reject_profile)),
        ):
            result = asyncio.run(service._build_workflow().ainvoke(state))

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["confidence_score"], 0)
        self.assertEqual(result["generated_profile"]["verification_status"], "unverified")
        self.assertEqual(result["generated_profile"]["sources"], [])
        self.assertIn(
            "not a verified company round",
            result["generated_profile"]["interview_rounds"]["Practice round 1"]["style"],
        )

    def test_pruning_reports_stale_entries_and_requires_explicit_apply(self):
        now = datetime(2026, 10, 30, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "discoveries.json"
            path.write_text(
                json.dumps([
                    {"company_name": "Old Co", "updated_at": "2025-01-01T00:00:00+00:00"},
                    {"company_name": "New Co", "updated_at": "2026-10-01T00:00:00+00:00"},
                ]),
                encoding="utf-8",
            )

            preview = prune_discoveries(path, 180, now=now)
            self.assertEqual(preview["stale_companies"], ["Old Co"])
            self.assertEqual(len(json.loads(path.read_text(encoding="utf-8"))), 2)

            applied = prune_discoveries(path, 180, apply_changes=True, now=now)
            self.assertEqual(applied["retained_count"], 1)
            self.assertEqual(
                json.loads(path.read_text(encoding="utf-8"))[0]["company_name"],
                "New Co",
            )


if __name__ == "__main__":
    unittest.main()
