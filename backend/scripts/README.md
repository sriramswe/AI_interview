# 🛠️ Utility Scripts

Maintenance scripts used for database management, reporting, and data validation.

## 📂 Available Scripts

1. **`generate_domain_report.py`**:
    - Reads all companies from `company_profiles.json` and `discoveries.json`.
    - Categorizes each company's industry using a priority-ordered `DOMAIN_MAPPER` (Finance & Accounting is checked before Business & Management to prevent miscategorization of firms like `Accounting/Consulting`).
    - Counts companies per domain and writes a formatted report to `data/DOMAIN_REPORT.md`.
    - Run: `python scripts/generate_domain_report.py`

2. **`add_company.py`**:
    - Manual entry tool for adding new curated profiles to `company_profiles.json`.
    - Edit the `NEW_COMPANY` dict at the top, then run the script.

3. **`test_company_intel.py`**:
    - Quick sanity check to verify a company is correctly retrievable from the curated or agentic database.
    - Used after adding a new company to confirm the fuzzy match works.

4. **`prune_discoveries.py`**:
    - Finds agent-discovered profiles that have not been refreshed for 180 days.
    - Preview only by default; stale discoveries are removed only when `--apply` is passed.
    - Schedule the command with your deployment's task scheduler to refresh discovery memory periodically.
    - Run preview: `python scripts/prune_discoveries.py`
    - Apply pruning: `python scripts/prune_discoveries.py --apply`

## 📊 Domain Report

The `DOMAIN_REPORT.md` is auto-generated — do not edit manually. Always run `generate_domain_report.py` after adding companies to keep the report in sync.
