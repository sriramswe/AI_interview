from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from services.gemini_service import gemini_service


class DevelopmentState(TypedDict, total=False):
    task: str
    plan: str
    backend_proposal: str
    database_proposal: str
    frontend_proposal: str
    integration_plan: str


class DevelopmentWorkflowAgents:
    def __init__(self, agent_call=gemini_service.generate_agent_output):
        self.agent_call = agent_call

    async def _call_agent(self, role: str, task: str, context: str = "") -> str:
        result = await self.agent_call(role=role, task=task, context=context)
        if not result.strip() or len(result) > 12000:
            raise RuntimeError(f"{role} returned an empty or oversized proposal.")
        return result.strip()

    async def planning_agent(self, state: DevelopmentState) -> dict[str, str]:
        plan = await self._call_agent(
            "Planning Agent",
            state["task"],
            "Break the task into a prioritized plan. Identify acceptance criteria, "
            "dependencies, risks, and work that can proceed in parallel. Do not assume "
            "files have been changed.",
        )
        return {"plan": plan}

    async def backend_agent(self, state: DevelopmentState) -> dict[str, str]:
        proposal = await self._call_agent(
            "Backend Agent (Python and FastAPI)",
            state["task"],
            state["plan"],
        )
        return {"backend_proposal": proposal}

    async def database_agent(self, state: DevelopmentState) -> dict[str, str]:
        proposal = await self._call_agent(
            "Database Agent",
            state["task"],
            state["plan"],
        )
        return {"database_proposal": proposal}

    async def frontend_agent(self, state: DevelopmentState) -> dict[str, str]:
        proposal = await self._call_agent(
            "Frontend Agent",
            state["task"],
            state["plan"],
        )
        return {"frontend_proposal": proposal}

    async def integration_agent(self, state: DevelopmentState) -> dict[str, str]:
        proposals = (
            f"Plan:\n{state['plan']}\n\n"
            f"Backend proposal:\n{state['backend_proposal']}\n\n"
            f"Database proposal:\n{state['database_proposal']}\n\n"
            f"Frontend proposal:\n{state['frontend_proposal']}"
        )
        result = await self._call_agent(
            "Integration Agent",
            state["task"],
            "Reconcile the parallel proposals into a single integration sequence. "
            "Call out API contracts, migration ordering, compatibility concerns, and "
            "acceptance checks. Do not claim implementation or tests have happened.\n\n"
            + proposals,
        )
        return {"integration_plan": result}

    def build_graph(self):
        graph = StateGraph(DevelopmentState)
        graph.add_node("planning", self.planning_agent)
        graph.add_node("backend", self.backend_agent)
        graph.add_node("database", self.database_agent)
        graph.add_node("frontend", self.frontend_agent)
        graph.add_node("integration", self.integration_agent)
        graph.set_entry_point("planning")
        graph.add_edge("planning", "backend")
        graph.add_edge("planning", "database")
        graph.add_edge("planning", "frontend")
        graph.add_edge(["backend", "database", "frontend"], "integration")
        graph.add_edge("integration", END)
        return graph.compile()

    async def create_proposals(self, task: str) -> dict[str, Any]:
        graph = self.build_graph()
        return await graph.ainvoke({"task": task})

    async def run_followup_agent(
        self, *, role: str, task: str, context: str
    ) -> str:
        return await self._call_agent(role, task, context)


development_workflow_agents = DevelopmentWorkflowAgents()
