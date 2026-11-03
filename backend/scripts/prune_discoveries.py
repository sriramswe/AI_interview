import argparse
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


DISCOVERIES_FILE = Path(__file__).resolve().parents[1] / "data" / "discoveries.json"


def _parse_updated_at(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp


def prune_discoveries(
    file_path: Path,
    older_than_days: int,
    apply_changes: bool = False,
    now: datetime | None = None,
) -> dict[str, Any]:
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least one.")
    if not file_path.exists():
        raise FileNotFoundError(f"Discovery memory does not exist: {file_path}")
    try:
        records = json.loads(file_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read discovery memory: {file_path}") from error
    if not isinstance(records, list):
        raise ValueError("Discovery memory must be a JSON list.")

    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=older_than_days)
    retained = []
    stale = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("Discovery memory contains a malformed record.")
        updated_at = _parse_updated_at(record.get("updated_at"))
        if updated_at is not None and updated_at < cutoff:
            stale.append(record)
        else:
            retained.append(record)

    if apply_changes and stale:
        temporary_file = file_path.with_suffix(file_path.suffix + ".tmp")
        try:
            temporary_file.write_text(
                json.dumps(retained, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary_file, file_path)
        except OSError as error:
            temporary_file.unlink(missing_ok=True)
            raise RuntimeError(f"Could not persist pruned discovery memory: {file_path}") from error

    return {
        "stale_count": len(stale),
        "retained_count": len(retained),
        "cutoff": cutoff.isoformat(),
        "applied": apply_changes,
        "stale_companies": [
            str(record.get("company_name") or "Unknown company")
            for record in stale
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove stale agent-discovery profiles so they are researched again."
    )
    parser.add_argument("--older-than-days", type=int, default=180)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write the pruned list. Without this option, only report stale entries.",
    )
    arguments = parser.parse_args()
    result = prune_discoveries(
        DISCOVERIES_FILE,
        arguments.older_than_days,
        apply_changes=arguments.apply,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
