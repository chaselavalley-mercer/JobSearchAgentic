"""
write_job_db.py — Scout Layer DB Writer
Layer: 3 (Execution)
Usage: from execution.write_job_db import write_job

Writes a validated, formatted job dict to the scout SQLite database.
Uses INSERT OR IGNORE for deduplication safety across parallel subagents.
"""

import os
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Literal

# ---------------------------------------------------------------------------
# Self-Source: load .env — honours PYTHONIOENCODING for correct output encoding
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
    _enc = os.environ.get("PYTHONIOENCODING", "")
    if _enc:
        sys.stdout.reconfigure(encoding=_enc)
        sys.stderr.reconfigure(encoding=_enc)
except (ImportError, AttributeError):
    pass


SOURCE_VALUES = Literal["linkedin_alert", "greenhouse_api", "playwright", "web_search"]


def _db_path(user_id: str) -> str:
    return os.path.join(".tmp", user_id, "scraped_jobs.db")


def write_job(
    job: dict,
    source: str,
    user_id: str,
) -> bool:
    """
    Write a job dict to the scout database.

    Returns True if the row was written (new), False if it was a duplicate.
    Raises sqlite3.OperationalError on connection failure after timeout.
    """
    path = _db_path(user_id)

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Scout DB not found at {path}. "
            "Run: python execution/init_db.py --user " + user_id
        )

    payload = job.get("analysis_payload", {}) or {}
    salary_warning = 1 if not job.get("pay_salary") else 0
    discovered_at = datetime.now(timezone.utc).isoformat()

    con = sqlite3.connect(path, timeout=10)
    try:
        cur = con.cursor()
        cur.execute(
            """
            INSERT OR IGNORE INTO jobs (
                url, job_title, company, location, work_arrangement,
                pay_salary, experience_level,
                core_responsibilities, required_qualifications, preferred_qualifications,
                salary_warning, source, discovered_at, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new')
            """,
            (
                job.get("url"),
                job.get("job_title"),
                job.get("company"),
                job.get("location"),
                job.get("work_arrangement"),
                job.get("pay_salary"),
                job.get("experience_level"),
                payload.get("core_responsibilities"),
                payload.get("required_qualifications"),
                payload.get("preferred_qualifications"),
                salary_warning,
                source,
                discovered_at,
            ),
        )
        con.commit()
        written = cur.rowcount > 0
    finally:
        con.close()

    label = "[WRITTEN]" if written else "[DUPLICATE]"
    print(f"{label} {job.get('url', '(no url)')} — {job.get('job_title', '')} @ {job.get('company', '')}")
    return written
