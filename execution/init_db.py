"""
init_db.py — Permanent Job Database Initializer
Layer: 3 (Execution)
Usage: python execution/init_db.py --user <user_id>

Creates (or no-ops if already exists):
  .users/{user_id}/jobs.db
    - evaluations table  (matches api.py + save_evaluation.py schema)
    - scout_log table

Safe to re-run at any time (CREATE TABLE IF NOT EXISTS).
"""

import argparse
import os
import sqlite3
import sys

# ---------------------------------------------------------------------------
# Self-Source: load .env
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


def init_db(user_id: str) -> str:
    # Permanent storage — lives in .users/, never in .tmp/
    db_dir = os.path.join(".users", user_id)
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "jobs.db")

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.executescript("""
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

        CREATE TABLE IF NOT EXISTS scout_log (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            session_at      TEXT,
            scout_type      TEXT,
            urls_found      INTEGER DEFAULT 0,
            urls_new        INTEGER DEFAULT 0,
            urls_written    INTEGER DEFAULT 0,
            urls_filtered   INTEGER DEFAULT 0,
            urls_failed     INTEGER DEFAULT 0,
            notes           TEXT
        );
    """)

    con.commit()
    con.close()

    print(f"[DB INIT] Database ready: {db_path}")
    return db_path


def main():
    parser = argparse.ArgumentParser(description="Initialize permanent jobs SQLite database.")
    parser.add_argument("--user", required=True, help="User ID (e.g. chase_lavalley)")
    args = parser.parse_args()
    init_db(args.user)


if __name__ == "__main__":
    main()