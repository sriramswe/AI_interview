import json
from pathlib import Path


class CompanyIntelligence:
    def __init__(self) -> None:
        profiles_path = Path(__file__).resolve().parents[1] / "data" / "company_profiles.json"
        try:
            data = json.loads(profiles_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError(
                f"Could not load curated company profiles from {profiles_path}."
            ) from error

        companies = data.get("companies") if isinstance(data, dict) else None
        if not isinstance(companies, dict):
            raise ValueError("Curated company profiles must contain a companies object.")

        self._profiles = {
            name.strip().casefold(): profile
            for name, profile in companies.items()
            if isinstance(name, str) and name.strip() and isinstance(profile, dict)
        }

    def get_all_companies(self) -> list[str]:
        return sorted(
            str(profile.get("name") or name)
            for name, profile in self._profiles.items()
        )

    def get_company(self, name: str) -> dict | None:
        return self._profiles.get(name.strip().casefold())


_company_intelligence = CompanyIntelligence()


def get_company_intelligence() -> CompanyIntelligence:
    return _company_intelligence
