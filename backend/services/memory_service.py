import asyncio
import json
from pathlib import Path


class MemoryService:
    def __init__(self) -> None:
        self._registry_path = Path(__file__).resolve().parents[1] / "data" / "stealth_registry.json"
        self._lock = asyncio.Lock()

    async def learn_from_session(self, session_data: dict) -> None:
        company = session_data.get("target_company")
        if not isinstance(company, str) or not company.strip():
            return
        async with self._lock:
            await asyncio.to_thread(self._update_registry, company.strip(), session_data)

    def _update_registry(self, company: str, session_data: dict) -> None:
        self._registry_path.parent.mkdir(parents=True, exist_ok=True)
        if self._registry_path.exists():
            registry = json.loads(self._registry_path.read_text(encoding="utf-8"))
            if not isinstance(registry, dict):
                raise ValueError("Company memory registry must contain a JSON object.")
        else:
            registry = {}
        current = registry.get(company, {})
        if not isinstance(current, dict):
            raise ValueError(f"Invalid company memory entry for {company}.")
        count = int(current.get("sessions", 0)) + 1
        previous_average = float(current.get("average_score", 0))
        score = float(session_data.get("score", 0))
        expert_sessions = int(current.get("expert_sessions", 0)) + int(score >= 8)
        witness_sessions = int(current.get("witness_sessions", 0)) + int(score <= 4)
        current.update(
            {
                "sessions": count,
                "hit_count": count,
                "average_score": round(
                    previous_average + (score - previous_average) / count, 2
                ),
                "expert_sessions": expert_sessions,
                "witness_sessions": witness_sessions,
                "consensus_score": round(
                    100 * (expert_sessions + witness_sessions) / count, 2
                ),
                "vetted": bool(current.get("vetted"))
                or (count >= 3 and expert_sessions > 0 and witness_sessions > 0),
                "roles": sorted(
                    set(current.get("roles", []))
                    | {str(session_data.get("role_category", ""))}
                    - {""}
                ),
                "rounds_seen": sorted(
                    set(current.get("rounds_seen", []))
                    | set(session_data.get("rounds_completed", []))
                ),
            }
        )
        registry[company] = current
        temporary_path = self._registry_path.with_suffix(".tmp")
        temporary_path.write_text(
            json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        temporary_path.replace(self._registry_path)


_memory_service = MemoryService()


def get_memory_service() -> MemoryService:
    return _memory_service
