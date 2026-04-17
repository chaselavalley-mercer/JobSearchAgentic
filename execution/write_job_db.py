"""
validate_db_row.py — DB-Native Schema Gate
Layer: 3 (Execution)
Usage: python execution/validate_db_row.py --user <user_id> --url <url>

Replaces validate_job_json.py. Queries the jobs.db row for the given URL
and checks that all required fields are non-null and non-empty.

Non-nullable (gate fails if missing):
  job_title, company, location, url,
  core_responsibilities, required_qualifications

Acceptable as null (gate passes regardless):
  pay_salary, benefits, experience_level,
  work_arrangement, preferred_qualifications

Exit codes:
  0 — All required fields present. Pipeline may proceed to Phase 3.
  1 — Validation failed. Prints missing fields. Do NOT proceed.
"""

import argparse
import os
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Self-Source .env
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv  # type: ignore
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
    _enc = os.environ.get("PYTHONIOENCODING", "")
    if _enc:
        import io
        if isinstance(sys.stdout, io.TextIOWrapper):
            sys.stdout.reconfigure(encoding=_enc)
        if isinstance(sys.stderr, io.TextIOWrapper):
            sys.stderr.reconfigure(encoding=_enc)
except (ImportError, AttributeError):
    pass


# ---------------------------------------------------------------------------
# Required fields definition
# ---------------------------------------------------------------------------
REQUIRED_FIELDS = [
    "job_title",
    "company",
    "location",
    "url",
    "core_responsibilities",
    "required_qualifications",
]

NULLABLE_FIELDS = [
    "pay_salary",
    "benefits",
    "experience_level",
    "work_arrangement",
    "preferred_qualifications",
]


# ---------------------------------------------------------------------------
# Validation logic
# ---------------------------------------------------------------------------
def validate_row(db_path: str, url: str) -> list[str]:
    """
    Returns a list of validation error strings.
    Empty list = valid, pipeline may proceed.
    """
    errors = []

    if not os.path.exists(db_path):
        return [f"Database not found: {db_path}"]

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    cur.execute("SELECT * FROM jobs WHERE url = ?", (url,))
    row = cur.fetchone()
    con.close()

    if row is None:
        return [f"No row found in jobs.db for URL: {url}"]

    row_dict = dict(row)

    for field in REQUIRED_FIELDS:
        value = row_dict.get(field)
        if value is None or str(value).strip() == "":
            errors.append(f"Required field is null or empty: '{field}'")

    return errors


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Validate a jobs.db row after scraping.")
    parser.add_argument("--user", required=True, help="User ID (e.g. chase_lavalley)")
    parser.add_argument("--url",  required=True, help="Job posting URL to validate")
    args = parser.parse_args()

    db_path = os.path.join(".users", args.user, "jobs.db")
    errors = validate_row(db_path, args.url)

    if errors:
        print("[GATE FAIL] DB validation failed. Fix the following before proceeding:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)

    # Print clean summary of validated row
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM jobs WHERE url = ?", (args.url,))
    row = dict(cur.fetchone())
    con.close()

    print("[GATE PASS] DB validation passed.")
    print(f"  Job Title  : {row.get('job_title', '')}")
    print(f"  Company    : {row.get('company', '')}")
    print(f"  Location   : {row.get('location', '')}")
    print(f"  URL        : {row.get('url', '')}")
    print(f"  Pay/Salary : {row.get('pay_salary', 'null — acceptable')}")
    print(f"  Exp Level  : {row.get('experience_level', 'null — acceptable')}")
    print(f"  Nullable fields present: {[f for f in NULLABLE_FIELDS if row.get(f)]}")
    sys.exit(0)


if __name__ == "__main__":
    main()