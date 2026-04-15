"""
init_db.py — Scout Layer Database Initializer
Layer: 3 (Execution)
Usage: python execution/init_db.py --user <user_id>

Creates (or no-ops if already exists):
  .tmp/{user_id}/scraped_jobs.db
    - jobs table
    - scout_log table

Safe to re-run at any time (CREATE TABLE IF NOT EXISTS).
"""

import argparse
import os
import sqlite3
import sys

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


def init_db(user_id: str) -> str:
    db_dir = os.path.join(".tmp", user_id)
    os.makedirs(db_dir, exist_ok=True)
    db_path = os.path.join(db_dir, "scraped_jobs.db")

    con = sqlite3.connect(db_path)
    cur = con.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            url                     TEXT PRIMARY KEY,
            job_title               TEXT,
            company                 TEXT,
            location                TEXT,
            work_arrangement        TEXT,
            pay_salary              TEXT,
            experience_level        TEXT,
            core_responsibilities   TEXT,
            required_qualifications TEXT,
            preferred_qualifications TEXT,
            salary_warning          INTEGER DEFAULT 0,
            source                  TEXT,
            discovered_at           TEXT,
            status                  TEXT DEFAULT 'new',
            evaluation_score        REAL,
            evaluation_card         TEXT,
            notes                   TEXT
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
    parser = argparse.ArgumentParser(description="Initialize scout layer SQLite database.")
    parser.add_argument("--user", required=True, help="User ID (e.g. chase_lavalley)")
    args = parser.parse_args()
    init_db(args.user)


if __name__ == "__main__":
    main()
