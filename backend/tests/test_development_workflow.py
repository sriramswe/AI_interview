import asyncio
import unittest

from services.development_workflow import DevelopmentWorkflowAgents


class DevelopmentWorkflowTests(unittest.TestCase):
    def test_planning_parallel_proposals_and_integration_are_connected(self):
        calls = []

        async def fake_agent_call(*, role, task, context):
            calls.append((role, task, context))
            return f"{role} proposal"

        agents = DevelopmentWorkflowAgents(agent_call=fake_agent_call)
        result = asyncio.run(agents.create_proposals("Add a health endpoint"))

        roles = {role for role, _, _ in calls}
        self.assertEqual(
            roles,
            {
                "Planning Agent",
                "Backend Agent (Python and FastAPI)",
                "Database Agent",
                "Frontend Agent",
                "Integration Agent",
            },
        )
        self.assertEqual(result["backend_proposal"], "Backend Agent (Python and FastAPI) proposal")
        self.assertEqual(result["database_proposal"], "Database Agent proposal")
        self.assertEqual(result["frontend_proposal"], "Frontend Agent proposal")
        self.assertIn("Integration Agent proposal", result["integration_plan"])
        self.assertTrue(all(task == "Add a health endpoint" for _, task, _ in calls))

    def test_empty_agent_output_is_an_explicit_failure(self):
        async def empty_agent_call(*, role, task, context):
            return " "

        agents = DevelopmentWorkflowAgents(agent_call=empty_agent_call)
        with self.assertRaisesRegex(RuntimeError, "empty or oversized"):
            asyncio.run(agents.create_proposals("Add a health endpoint"))


if __name__ == "__main__":
    unittest.main()
