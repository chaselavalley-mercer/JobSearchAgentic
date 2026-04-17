"""
save_evaluation.py — Persist Evaluation Card to SQLite
Layer: 3 (Execution)

Reads .tmp/{user_id}/evaluation_card.json and writes to
.users/{user_id}/jobs.db. One row per job. Re-evaluation overwrites.

Usage:
    python execution/save_evaluation.py --user chase_lavalley

Exit codes:
    0 — Success
    1 — Missing evaluation_card.json or malformed JSON
    2 — Database write error
"""

import sys
import os
import json
import sqlite3
import argparse
from datetime import datetime

# ---------------------------------------------------------------------------
# Self-Source: load .env — honours PYTHONIOENCODING for correct output encoding
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
# Schema
# ---------------------------------------------------------------------------

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS evaluations (
    job_id              TEXT PRIMARY KEY,
    evaluated_at        TEXT,
    title               TEXT,
    company             TEXT,
    location            TEXT,
    url                 TEXT,
    experience_level    TEXT,
    pay_salary          TEXT,
    work_arrangement    TEXT,
    application_count   INTEGER,
    benefits            TEXT,
    posted_date         TEXT,
    gate_passed         INTEGER,
    gate_details        TEXT,
    null_fields         TEXT,
    scores              TEXT,
    composite_score     REAL,
    grade               TEXT,
    recommendation      TEXT,
    gaps                TEXT
);
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def build_job_id(company: str, title: str, location: str) -> str:
    """Derive a stable unique key from company + title + location."""
    raw = f"{company}_{title}_{location}"
    return raw.lower().replace(" ", "_").replace(",", "").replace(".", "")


def load_card(card_path: str) -> dict:
    if not os.path.exists(card_path):
        print(f"[!] evaluation_card.json not found at: {card_path}")
        sys.exit(1)

    with open(card_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"[!] Malformed JSON in evaluation_card.json: {e}")
            sys.exit(1)


def card_to_row(card: dict) -> dict:
    """Flatten evaluation card into a single table row."""
    job = card.get("job_data", {})
    gate = card.get("gate_pass", {})

    company  = job.get("company", "unknown")
    title    = job.get("title", "unknown")
    location = job.get("location", "unknown")

    return {
        "job_id":            build_job_id(company, title, location),
        "evaluated_at":      card.get("evaluated_at", datetime.now().isoformat()),
        "title":             title,
        "company":           company,
        "location":          location,
        "url":               job.get("url"),
        "experience_level":  job.get("experience_level"),
        "pay_salary":        job.get("pay_salary"),
        "work_arrangement":  job.get("work_arrangement"),
        "application_count": job.get("application_count"),
        "benefits":          json.dumps(job.get("benefits", [])),
        "posted_date":       job.get("posted_date"),
        "gate_passed":       1 if gate.get("passed") else 0,
        "gate_details":      json.dumps(gate.get("gates", {})),
        "null_fields":       json.dumps(card.get("null_fields", [])),
        "scores":            json.dumps(card.get("scores", {})),
        "composite_score":   card.get("composite_score"),
        "grade":             card.get("grade"),
        "recommendation":    card.get("recommendation"),
        "gaps":              json.dumps(card.get("decision_card", {}).get("gaps", [])),
    }


def save_to_db(row: dict, db_path: str):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        cursor.execute(CREATE_TABLE_SQL)

        cursor.execute("""
            INSERT OR REPLACE INTO evaluations (
                job_id, evaluated_at, title, company, location, url,
                experience_level, pay_salary, work_arrangement,
                application_count, benefits, posted_date,
                gate_passed, gate_details, null_fields,
                scores, composite_score, grade, recommendation, gaps
            ) VALUES (
                :job_id, :evaluated_at, :title, :company, :location, :url,
                :experience_level, :pay_salary, :work_arrangement,
                :application_count, :benefits, :posted_date,
                :gate_passed, :gate_details, :null_fields,
                :scores, :composite_score, :grade, :recommendation, :gaps
            )
        """, row)

        conn.commit()
        conn.close()

        print(f"[*] Saved: {row['job_id']}")
        print(f"[*] Database: {db_path}")
        print(f"[*] Score: {row['composite_score']} [{row['grade']}] — {row['recommendation']}")

    except sqlite3.Error as e:
        print(f"[!] Database error: {e}")
        sys.exit(2)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Persist evaluation card to SQLite")
    parser.add_argument("--user", default="chase_lavalley", help="User ID")
    args = parser.parse_args()

    card_path = os.path.join(".tmp", args.user, "evaluation_card.json")
    db_path   = os.path.join(".users", args.user, "jobs.db")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    card = load_card(card_path)
    row  = card_to_row(card)
    save_to_db(row, db_path)


if __name__ == "__main__":
    main()