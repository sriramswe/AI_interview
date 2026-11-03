import os
import json
import asyncio
import logging
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from typing_extensions import TypedDict

from langgraph.graph import StateGraph, END
from duckduckgo_search import DDGS

from services.company_intelligence import get_company_intelligence
from services.gemini_service import gemini_service

class AgentState(TypedDict):
    company_name: str
    industry: Optional[str]
    geography: Optional[str]
    requested_geography: Optional[str]
    job_description: Optional[str]
    research_data: Optional[str]
    is_synthetic: bool
    confidence_score: int
    generated_profile: Optional[Dict[str, Any]]
    is_valid: bool
    iterations: int
    sources: List[Dict[str, str]]
    search_query: Optional[str]
    audited_data: Optional[str]
    audit_log: List[str]
    critic_feedback: Optional[str]
    error: Optional[str]


logger = logging.getLogger(__name__)


class ProductionIntelligenceService:
    def __init__(self):
        self.base_dir = Path(__file__).resolve().parents[1]
        self.data_dir = self.base_dir / "data"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._active_discoveries: Dict[str, asyncio.Task] = {}
        self._background_discoveries: Dict[str, asyncio.Task] = {}
        self._progress: Dict[str, dict] = {}
        self._fs_lock = asyncio.Lock()

    @staticmethod
    def _discovery_key(company: str, geography: str | None = None) -> str:
        return f"{company.strip().casefold()}::{(geography or '').strip().casefold()}"

    def get_discovery_status(self, company: str, geography: str | None = None) -> dict:
        key = self._discovery_key(company, geography)
        return self._progress.get(key, {
            "company": company.strip(),
            "geography": geography,
            "status": "idle",
            "stage": "Idle",
            "mode": None,
            "events": [],
        })

    def _trim_progress(self) -> None:
        while len(self._progress) > 100:
            oldest_key = next(
                (
                    key
                    for key, progress in self._progress.items()
                    if progress.get("status") != "running"
                ),
                None,
            )
            if oldest_key is None:
                break
            self._progress.pop(oldest_key, None)

    async def start_discovery(
        self,
        company: str,
        job_description: str | None = None,
        geography: str | None = None,
    ) -> dict:
        clean_name = company.strip()
        region = geography.strip() if geography and geography.strip() else None
        key = self._discovery_key(clean_name, region)
        existing = self._background_discoveries.get(key)
        if existing and not existing.done():
            return {"company": clean_name, "geography": region, "status": "running"}

        self._progress[key] = {
            "company": clean_name,
            "geography": region,
            "status": "running",
            "stage": "Routing",
            "mode": None,
            "events": [{"message": "Routing company, role, and geography.", "decision": "INFO"}],
        }
        self._trim_progress()

        async def run() -> None:
            try:
                await self.get_intelligence(clean_name, job_description, region)
                self._record_progress(
                    clean_name, region, "completed", "Completed",
                    "Company profile passed critic review and was saved.", "ACCEPTED",
                )
                self._progress[key]["status"] = "completed"
            except Exception as error:
                logger.exception("Company discovery failed for %s", clean_name)
                self._record_progress(
                    clean_name, region, "failed", "Failed",
                    "Company research could not be completed. Review server logs for details.", "ERROR",
                )
                self._progress[key]["status"] = "failed"
                self._progress[key]["error"] = (
                    "Company research failed. Verify the backend AI and search provider configuration."
                )

        task = asyncio.create_task(run())
        self._background_discoveries[key] = task

        def forget_finished_task(finished_task: asyncio.Task) -> None:
            if self._background_discoveries.get(key) is finished_task:
                self._background_discoveries.pop(key, None)

        task.add_done_callback(forget_finished_task)
        return {"company": clean_name, "geography": region, "status": "running"}

    def _record_progress(
        self,
        company: str,
        geography: str | None,
        stage: str,
        message: str,
        decision: str = "INFO",
        mode: str | None = None,
        url: str | None = None,
    ) -> None:
        key = self._discovery_key(company, geography)
        if key not in self._progress:
            company_prefix = f"{company.strip().casefold()}::"
            active_matches = [
                candidate
                for candidate, progress in self._progress.items()
                if candidate.startswith(company_prefix) and progress.get("status") == "running"
            ]
            if len(active_matches) == 1:
                key = active_matches[0]
        progress = self._progress.setdefault(key, {
            "company": company.strip(),
            "geography": geography,
            "status": "running",
            "stage": stage,
            "mode": mode,
            "events": [],
        })
        progress["stage"] = stage
        if mode:
            progress["mode"] = mode
        progress["events"] = [
            *progress.get("events", []),
            {
                "message": message[:1000],
                "decision": decision,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ][-50:]

    async def router_node(self, state: AgentState) -> AgentState:
        company_name = state["company_name"]
        jd_context = state.get("job_description", "")
        requested_geography = state.get("requested_geography")
        current_year = datetime.now().year

        prompt = f"""
        Analyze this company: '{company_name}'
        User Job Description: {jd_context or 'None provided'}
        Requested interview region: {requested_geography or 'Not specified'}
        Current Year: {current_year}

        TASKS:
        1. Identify the likely industry and geographic headquarters/process. Prefer
           the requested interview region when it is provided; do not silently substitute
           headquarters location for the requested hiring market.
        2. Generate a focused search query for interview processes and culture.
        3. Do NOT assume software engineering roles unless the JD asks for it.

        Return ONLY a JSON dictionary:
        {{
            "suggested_query": "{company_name} interview questions process {current_year}",
            "detected_industry": "Tech/Finance/Healthcare/Retail/etc.",
            "detected_geography": "country or region, or null if unknown",
            "reasoning": "brief logic"
        }}
        """
        try:
            raw_response = await gemini_service._generate(prompt)
            clean = raw_response.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            res = json.loads(clean)
            state["search_query"] = res.get("suggested_query", f"{company_name} interview process {current_year}")
            state["industry"] = res.get("detected_industry", "General Industry")
            detected = res.get("detected_geography")
            state["geography"] = requested_geography or (
                detected.strip() if isinstance(detected, str) and detected.strip() else None
            )
        except (json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
            logger.warning("Company router returned invalid discovery data: %s", error)
            state["search_query"] = f"{company_name} interview questions process {current_year}"
            state["industry"] = "General Industry"
            state["geography"] = requested_geography
        if requested_geography and requested_geography.casefold() not in state["search_query"].casefold():
            state["search_query"] = f"{state['search_query']} {requested_geography}"
        self._record_progress(
            company_name, requested_geography, "Researching",
            f"Research query routed for {state.get('industry') or 'the identified industry'}"
            + (f" in {state['geography']}" if state.get("geography") else "."),
        )

        return state

    async def researcher_node(self, state: AgentState) -> AgentState:
        query = state.get("search_query") or f"{state['company_name']} interview questions"
        geography = state.get("geography")
        if geography and geography.casefold() not in query.casefold():
            query = f"{query} {geography}"
        self._record_progress(
            state["company_name"], state.get("requested_geography"), "Researching",
            f"Searching current public sources for {state['company_name']}."
            + (f" Region: {geography}." if geography else ""),
        )

        def _search():
            last_error = None
            for attempt in range(3):
                try:
                    with DDGS(timeout=5) as ddgs:
                        return list(ddgs.text(query, max_results=6))
                except Exception as error:
                    last_error = error
                    if attempt < 2:
                        time.sleep((0.4 * (2 ** attempt)) + random.uniform(0, 0.15))
            raise RuntimeError("Public company research failed after three attempts.") from last_error

        try:
            results = await asyncio.wait_for(asyncio.to_thread(_search), timeout=18.0)
        except asyncio.TimeoutError:
            raise RuntimeError("Public company research timed out after retrying.")

        if not results:
            state["is_synthetic"] = True
            state["confidence_score"] = 25
            state["research_data"] = "Stealth or private enterprise. Applying industry-standard baseline heuristics."
            state["sources"] = []
            self._record_progress(
                state["company_name"], state.get("requested_geography"), "Auditing",
                "No public search results were returned; using a clearly labeled stealth profile.",
                "INFO", "stealth",
            )
            return state

        # Strip SEO content farms that contaminate evaluation
        GENERIC_SEO_DOMAINS = [
            "datacamp.com", "guru99.com", "intellipaat.com", "interviewbit.com",
            "geeksforgeeks.org", "theysaid.io", "interviewsidekick.com", "simplilearn.com",
            "analyticsvidhya.com", "javatpoint.com", "edureka.co"
        ]
        filtered = [r for r in results if not any(domain in r.get("href", "") for domain in GENERIC_SEO_DOMAINS)]
        active_results = filtered if filtered else results

        state["is_synthetic"] = False
        state["confidence_score"] = min(90, len(active_results) * 18)
        state["research_data"] = "\n".join([f"Source ({r['title']}): {r['body']}" for r in active_results])
        state["sources"] = [{"title": r["title"], "url": r["href"]} for r in active_results]
        self._record_progress(
            state["company_name"], state.get("requested_geography"), "Auditing",
            f"Collected {len(active_results)} public source snippets for identity and relevance review.",
            "INFO", "public",
        )
        return state

    async def auditor_node(self, state: AgentState) -> AgentState:
        self._record_progress(
            state["company_name"], state.get("requested_geography"), "Auditing",
            "Auditing sources for company identity, region, and role relevance.",
        )
        if state["is_synthetic"]:
            state["audited_data"] = state["research_data"]
            state["is_valid"] = True
            return state

        prompt = f"""
        Audit these search snippets for target company '{state['company_name']}'.
        Candidate Target Industry: {state.get('industry')}
        Candidate Target Geography: {state.get('geography')}
        Data:
        {state['research_data']}

        TASKS:
        1. Reject snippets referring to completely different entities with similar acronyms.
        2. Keep only authentic company interview styles, rounds, culture, and difficulty.
        3. Return a decision for each supplied source. Decisions must be ACCEPTED or
           REJECTED and include the source URL and a short evidence-based reason.

        Return ONLY a JSON dictionary:
        {{
            "is_identity_verified": true,
            "cleaned_snippets": "purged content",
            "confidence_adjustment": 5,
            "source_decisions": [{{"url": "source URL", "decision": "ACCEPTED", "reason": "identity and relevance"}}]
        }}
        """
        try:
            raw = await gemini_service._generate(prompt)
            clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(clean)
            verified = data.get("is_identity_verified")
            if not isinstance(verified, bool):
                raise ValueError("Auditor verdict must include a boolean identity decision.")
            if not verified:
                state["is_synthetic"] = True
                state["confidence_score"] = 25
                state["audited_data"] = (
                    "Search result identity could not be verified. Use only "
                    "industry and job-description evidence."
                )
                state["sources"] = []
                state["is_valid"] = True
                return state
            cleaned_snippets = data.get("cleaned_snippets")
            if not isinstance(cleaned_snippets, str) or not cleaned_snippets.strip():
                raise ValueError("Auditor did not return verified company information.")
            decisions = data.get("source_decisions")
            if not isinstance(decisions, list):
                raise ValueError("Auditor did not return source decisions.")
            decision_map = {
                item.get("url"): item
                for item in decisions
                if isinstance(item, dict)
                and isinstance(item.get("url"), str)
                and item.get("decision") in {"ACCEPTED", "REJECTED"}
                and isinstance(item.get("reason"), str)
            }
            source_urls = {source["url"] for source in state["sources"]}
            if len(decision_map) != len(state["sources"]) or set(decision_map) != source_urls:
                raise ValueError("Auditor source decisions did not cover all supplied sources.")
            accepted_sources = []
            for source in state["sources"]:
                decision = decision_map.get(source["url"])
                self._record_progress(
                    state["company_name"],
                    state.get("requested_geography"),
                    "Auditing",
                    f"{decision['decision']}: {source['title']} — {decision['reason']}",
                    decision["decision"],
                    url=source["url"],
                )
                if decision["decision"] == "ACCEPTED":
                    accepted_sources.append(source)
            state["sources"] = accepted_sources
            state["audited_data"] = cleaned_snippets
            adjustment = int(data.get("confidence_adjustment", 0))
            state["confidence_score"] = max(
                0, min(100, state["confidence_score"] + adjustment)
            )
            state["is_valid"] = True
        except Exception as error:
            raise RuntimeError("Company intelligence audit failed.") from error

        return state

    async def architect_node(self, state: AgentState) -> AgentState:
        self._record_progress(
            state["company_name"], state.get("requested_geography"), "Architecting",
            "Building a domain-aware interview profile from audited evidence.",
        )
        prompt = f"""
        Build an Interview Profile for '{state['company_name']}' in industry '{state.get('industry')}'.
        Job Description: {state.get('job_description') or 'Standard'}
        Verified Research: {state.get('audited_data')}
        Critic feedback to address: {state.get('critic_feedback') or 'None'}

        CRITICAL BIAS RULE:
        If industry is non-tech (Healthcare, Legal, etc.), do NOT force LeetCode or coding rounds unless specified.

        Return ONLY valid JSON matching this schema:
        {{
            "company_name": "{state['company_name']}",
            "industry": "{state.get('industry')}",
            "interview_style": "string",
            "difficulty_level": "Beginner/Intermediate/Hard",
            "cultural_values": ["value1", "value2"],
            "interview_rounds": {{
                "Round 1": {{"focus": "string", "style": "string"}},
                "Round 2": {{"focus": "string", "style": "string"}}
            }},
            "tips": ["tip1", "tip2"]
        }}
        """
        raw = await gemini_service._generate(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            profile = json.loads(clean)
        except json.JSONDecodeError as error:
            raise RuntimeError("Company architect returned invalid profile JSON.") from error
        if not isinstance(profile, dict):
            raise RuntimeError("Company architect must return a JSON object.")
        state["generated_profile"] = profile
        state["iterations"] += 1
        return state

    async def critic_node(self, state: AgentState) -> AgentState:
        self._record_progress(
            state["company_name"], state.get("requested_geography"), "Critic review",
            "Critically checking identity, role fit, and unsupported company claims.",
        )
        profile = state.get("generated_profile") or {}
        required_fields = (
            "company_name",
            "industry",
            "interview_style",
            "difficulty_level",
            "cultural_values",
            "interview_rounds",
            "tips",
        )
        missing_fields = [
            field
            for field in required_fields
            if field not in profile or profile[field] in (None, "", [], {})
        ]
        invalid_fields = [
            field
            for field, expected_type in (
                ("company_name", str),
                ("industry", str),
                ("interview_style", str),
                ("difficulty_level", str),
                ("cultural_values", list),
                ("interview_rounds", dict),
                ("tips", list),
            )
            if field in profile and not isinstance(profile[field], expected_type)
        ]
        identity_matches = (
            str(profile.get("company_name", "")).strip().casefold()
            == state["company_name"].strip().casefold()
        )
        if missing_fields or invalid_fields or not identity_matches:
            state["is_valid"] = False
            state["critic_feedback"] = (
                f"Fix missing fields {missing_fields}, invalid fields {invalid_fields}, "
                "and ensure the profile "
                "identifies the requested company exactly."
            )
            return state

        prompt = f"""
        Critically validate this interview profile for '{state['company_name']}'.
        Industry: {state.get('industry')}
        Geography: {state.get('geography')}
        Job description: {state.get('job_description') or 'Not provided'}
        Audited research: {state.get('audited_data') or 'Synthetic industry baseline'}
        Profile: {json.dumps(profile, ensure_ascii=False)}

        Check that the company identity, hiring-market geography, role, and industry
        agree with the evidence. Verify every company-specific interview stage,
        technology, value, and culture claim against audited evidence; reject
        unsupported specificity instead of guessing. Require region-specific
        distinctions to be grounded in evidence for that region. Reject claims that
        imply the sources guarantee the same process for every team or candidate.
        Do not require public sources for a clearly labeled synthetic stealth profile.
        Reject coding-round requirements for non-technical roles unless the job
        description requires them. Preserve uncertainty and lower confidence when
        evidence is sparse.
        Return only JSON with "approved" (boolean), "feedback" (string), and
        "confidence_adjustment" (integer from -20 to 10).
        """
        raw = await gemini_service._generate(prompt)
        clean = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            verdict = json.loads(clean)
        except json.JSONDecodeError as error:
            raise RuntimeError("Company critic returned invalid JSON.") from error
        if (
            not isinstance(verdict, dict)
            or not isinstance(verdict.get("approved"), bool)
            or not isinstance(verdict.get("feedback"), str)
        ):
            raise RuntimeError("Company critic returned an invalid verdict.")

        state["is_valid"] = verdict["approved"]
        state["critic_feedback"] = verdict["feedback"]
        try:
            adjustment = int(verdict.get("confidence_adjustment", 0))
        except (TypeError, ValueError) as error:
            raise RuntimeError("Company critic returned an invalid confidence adjustment.") from error
        state["confidence_score"] = max(
            0, min(100, state["confidence_score"] + adjustment)
        )
        return state

    @staticmethod
    def _critic_decision(state: AgentState) -> str:
        if state.get("is_valid"):
            return "approve"
        if state.get("iterations", 0) < 2:
            return "revise"
        raise RuntimeError(
            f"Company profile failed critic review: {state.get('critic_feedback')}"
        )

    def _build_workflow(self):
        wf = StateGraph(AgentState)
        wf.add_node("router", self.router_node)
        wf.add_node("researcher", self.researcher_node)
        wf.add_node("auditor", self.auditor_node)
        wf.add_node("architect", self.architect_node)
        wf.add_node("critic", self.critic_node)

        wf.set_entry_point("router")
        wf.add_edge("router", "researcher")
        wf.add_edge("researcher", "auditor")
        wf.add_edge("auditor", "architect")
        wf.add_edge("architect", "critic")
        wf.add_conditional_edges(
            "critic",
            self._critic_decision,
            {"approve": END, "revise": "architect"},
        )
        return wf.compile()

    async def get_intelligence(
        self,
        company: str | None,
        job_description: str | None = None,
        geography: str | None = None,
    ) -> dict | None:
        if not company or not company.strip():
            return None

        clean_name = company.strip()
        region = geography.strip() if geography and geography.strip() else None
        normalized_name = self._discovery_key(clean_name, region)
        self._progress.setdefault(normalized_name, {
            "company": clean_name,
            "geography": region,
            "status": "running",
            "stage": "Routing",
            "mode": None,
            "events": [],
        })
        self._trim_progress()

        # 1. Fast Cache Check: Static Profiles
        static_intel = get_company_intelligence().get_company(clean_name)
        if static_intel and (
            not region
            or str(static_intel.get("geography") or "").casefold() == region.casefold()
        ):
            self._progress[normalized_name].update(
                {"status": "completed", "stage": "Completed", "mode": "curated"}
            )
            self._record_progress(
                clean_name, region, "Completed",
                "Loaded the curated company profile.", "ACCEPTED", "curated",
            )
            return static_intel

        # 2. Tiered File Cache Check
        cache_file = self.data_dir / "discoveries.json"
        async with self._fs_lock:
            if cache_file.exists():
                try:
                    records = json.loads(cache_file.read_text(encoding="utf-8"))
                    if isinstance(records, dict):
                        profile = records.get(clean_name.casefold())
                        if isinstance(profile, dict) and (
                            not region
                            or str(profile.get("geography") or "").casefold() == region.casefold()
                        ):
                            self._progress[normalized_name].update(
                                {"status": "completed", "stage": "Completed", "mode": "public"}
                            )
                            return profile
                    elif isinstance(records, list):
                        for item in records:
                            if (
                                isinstance(item, dict)
                                and isinstance(item.get("company_name"), str)
                                and item["company_name"].casefold() == clean_name.casefold()
                                and (
                                    not region
                                    or str(item.get("geography") or item.get("profile", {}).get("geography") or "").casefold()
                                    == region.casefold()
                                )
                            ):
                                cached_profile = item.get("profile", item)
                                self._progress[normalized_name].update(
                                    {"status": "completed", "stage": "Completed", "mode": "public"}
                                )
                                return cached_profile
                    else:
                        raise ValueError("Company discovery cache has an invalid shape.")
                except (OSError, json.JSONDecodeError, ValueError) as error:
                    raise RuntimeError("Could not read the company discovery cache.") from error

        # 3. Deduplicate active network/AI searches
        if normalized_name in self._active_discoveries:
            return await self._active_discoveries[normalized_name]

        async def _run_workflow():
            try:
                workflow = self._build_workflow()
                initial_state: AgentState = {
                    "company_name": clean_name,
                    "industry": None,
                    "geography": region,
                    "requested_geography": region,
                    "job_description": job_description,
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
                    "error": None
                }
                final_state = await workflow.ainvoke(initial_state)
                if not final_state.get("is_valid"):
                    raise RuntimeError(
                        f"Company profile failed critic review: {final_state.get('critic_feedback')}"
                    )
                profile = final_state.get("generated_profile") or {}
                profile.update(
                    {
                        "confidence_score": final_state["confidence_score"],
                        "is_synthetic": final_state["is_synthetic"],
                        "sources": final_state["sources"],
                        "geography": final_state.get("geography"),
                    }
                )

                # 4. Thread-Safe File Persistence
                async with self._fs_lock:
                    records = []
                    if cache_file.exists():
                        try:
                            records = json.loads(cache_file.read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError) as error:
                            raise RuntimeError(
                                "Could not read the company discovery cache for update."
                            ) from error
                        if not isinstance(records, list):
                            raise ValueError(
                                "Company discovery cache must contain a JSON list."
                            )
                    records.append({
                        "company_name": clean_name,
                        "geography": final_state.get("geography"),
                        "profile": profile,
                        "updated_at": datetime.now(timezone.utc).isoformat()
                    })
                    temporary_cache = cache_file.with_suffix(".tmp")
                    temporary_cache.write_text(
                        json.dumps(records, ensure_ascii=False, indent=2),
                        encoding="utf-8",
                    )
                    temporary_cache.replace(cache_file)

                return profile
            except Exception:
                self._progress[normalized_name]["status"] = "failed"
                self._progress[normalized_name]["error"] = (
                    "Company intelligence could not be generated. Check backend logs."
                )
                raise
            finally:
                if self._progress[normalized_name].get("status") != "failed":
                    self._progress[normalized_name]["status"] = "completed"
                    self._progress[normalized_name]["stage"] = "Completed"
                self._active_discoveries.pop(normalized_name, None)

        task = asyncio.create_task(_run_workflow())
        self._active_discoveries[normalized_name] = task
        return await task


_service = ProductionIntelligenceService()

def get_intelligence_service(eager_load: bool = False) -> ProductionIntelligenceService:
    del eager_load
    return _service