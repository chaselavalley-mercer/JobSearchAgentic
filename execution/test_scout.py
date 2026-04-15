"""
test_scout.py — End-to-End Scout Pipeline Validation
Layer: 3 (Execution)
Usage: python execution/test_scout.py

Validates:
  Part 1 — Unit tests (no network, no browser)
  Part 2 — Integration test (live Greenhouse API + DB write)
  Part 3 — Log file validation

Exit codes:
  0  — All tests passed
  1  — One or more tests failed
"""

import json
import os
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Path setup — allow running from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

# ---------------------------------------------------------------------------
# Self-Source: load .env — honours PYTHONIOENCODING for correct output encoding
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(PROJECT_ROOT, ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
    _enc = os.environ.get("PYTHONIOENCODING", "")
    if _enc:
        sys.stdout.reconfigure(encoding=_enc)
        sys.stderr.reconfigure(encoding=_enc)
except (ImportError, AttributeError):
    pass

from execution.format_job import format_job
from execution.validate_job import validate
from execution.write_job_db import write_job
from execution.init_db import init_db

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
USER_ID = "chase_lavalley"
TEST_DB_PATH = os.path.join(".tmp", USER_ID, "test_scout.db")
TODAY = datetime.now(timezone.utc).strftime("%Y-%m-%d")
LOG_DIR = os.path.join("logs", USER_ID)
LOG_PATH = os.path.join(LOG_DIR, f"scout_{TODAY}.log")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[32mPASS\033[0m"
FAIL = "\033[31mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def record(label: str, passed: bool, detail: str = ""):
    results.append((label, passed, detail))
    status = PASS if passed else FAIL
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'='*56}")
    print(f"  {title}")
    print(f"{'='*56}")


def _init_test_db() -> str:
    """Provision a fresh test DB separate from the production scout DB."""
    os.makedirs(os.path.dirname(TEST_DB_PATH), exist_ok=True)
    # Remove stale test DB so unit tests start clean
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    con = sqlite3.connect(TEST_DB_PATH)
    con.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
            url TEXT PRIMARY KEY,
            job_title TEXT, company TEXT, location TEXT,
            work_arrangement TEXT, pay_salary TEXT, experience_level TEXT,
            core_responsibilities TEXT, required_qualifications TEXT,
            preferred_qualifications TEXT,
            salary_warning INTEGER DEFAULT 0, source TEXT,
            discovered_at TEXT, status TEXT DEFAULT 'new',
            evaluation_score REAL, evaluation_card TEXT, notes TEXT
        );
        CREATE TABLE IF NOT EXISTS scout_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_at TEXT, scout_type TEXT, urls_found INTEGER DEFAULT 0,
            urls_new INTEGER DEFAULT 0, urls_written INTEGER DEFAULT 0,
            urls_filtered INTEGER DEFAULT 0, urls_failed INTEGER DEFAULT 0,
            notes TEXT
        );
    """)
    con.commit()
    con.close()
    return TEST_DB_PATH


def _write_log(line: str):
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def _write_job_test_db(job: dict, source: str) -> bool:
    """write_job wrapper that targets the TEST db, not production."""
    import sqlite3 as _sq3
    from datetime import datetime, timezone as _tz

    path = TEST_DB_PATH
    payload = job.get("analysis_payload", {}) or {}
    salary_warning = 1 if not job.get("pay_salary") else 0
    discovered_at = datetime.now(_tz.utc).isoformat()

    con = _sq3.connect(path, timeout=10)
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
                job.get("url"), job.get("job_title"), job.get("company"),
                job.get("location"), job.get("work_arrangement"),
                job.get("pay_salary"), job.get("experience_level"),
                payload.get("core_responsibilities"),
                payload.get("required_qualifications"),
                payload.get("preferred_qualifications"),
                salary_warning, source, discovered_at,
            ),
        )
        con.commit()
        written = cur.rowcount > 0
    finally:
        con.close()

    label = "[WRITTEN]" if written else "[DUPLICATE]"
    print(f"    {label} {job.get('url', '')}")
    return written


# ---------------------------------------------------------------------------
# PART 1 — Unit Tests
# ---------------------------------------------------------------------------

def test_format_job_unit():
    section("PART 1 — format_job unit tests")

    # --- location normalization ---
    r = format_job({
        "job_title": "AI Engineer", "company": "Acme", "url": "https://x.com/1",
        "location": "Atlanta, GA (Hybrid)",
        "analysis_payload": {
            "core_responsibilities": "Build models",
            "required_qualifications": "Python",
            "preferred_qualifications": "PyTorch",
        },
    })
    record("location strip parenthetical", r["location"] == "Atlanta, GA",
           f"got: {r['location']!r}")
    record("work_arrangement from location keyword", r["work_arrangement"] == "Hybrid",
           f"got: {r['work_arrangement']!r}")

    # --- Remote - US Only ---
    r2 = format_job({
        "job_title": "ML Engineer", "company": "OpenAI", "url": "https://x.com/2",
        "location": "Remote - US Only",
        "analysis_payload": {
            "core_responsibilities": "Train LLMs",
            "required_qualifications": "Python",
            "preferred_qualifications": "CUDA",
        },
    })
    record("location Remote strip suffix", r2["location"] == "Remote",
           f"got: {r2['location']!r}")
    record("work_arrangement Remote inferred", r2["work_arrangement"] == "Remote",
           f"got: {r2['work_arrangement']!r}")

    # --- pay_salary normalization ---
    r3 = format_job({
        "job_title": "Data Scientist", "company": "Cohere", "url": "https://x.com/3",
        "location": "Remote",
        "pay_salary": "$120,000 - $160,000/year plus equity",
        "analysis_payload": {
            "core_responsibilities": "Model training",
            "required_qualifications": "Python",
            "preferred_qualifications": "TensorFlow",
        },
    })
    record("pay_salary range extraction",
           r3["pay_salary"] == "$120,000 - $160,000",
           f"got: {r3['pay_salary']!r}")

    r4 = format_job({
        "job_title": "SWE", "company": "X", "url": "https://x.com/4",
        "location": "Atlanta, GA",
        "pay_salary": "Competitive salary",
        "analysis_payload": {
            "core_responsibilities": "Code",
            "required_qualifications": "Python",
            "preferred_qualifications": "Go",
        },
    })
    record("pay_salary vague phrase -> None",
           r4["pay_salary"] is None,
           f"got: {r4['pay_salary']!r}")

    # --- experience_level ---
    r5 = format_job({
        "job_title": "AI Researcher", "company": "Waymo", "url": "https://x.com/5",
        "location": "Remote",
        "experience_level": "2-4 years of experience in ML",
        "analysis_payload": {
            "core_responsibilities": "Research",
            "required_qualifications": "PhD",
            "preferred_qualifications": "Publications",
        },
    })
    record("experience_level strip trailing context",
           r5["experience_level"] == "2-4 years",
           f"got: {r5['experience_level']!r}")

    # --- job_title strip ---
    r6 = format_job({
        "job_title": "AI Engineer - Remote", "company": "Scale AI",
        "url": "https://x.com/6",
        "location": "Remote",
        "analysis_payload": {
            "core_responsibilities": "Label data",
            "required_qualifications": "Python",
            "preferred_qualifications": "SQL",
        },
    })
    record("job_title strip trailing location tag",
           r6["job_title"] == "AI Engineer",
           f"got: {r6['job_title']!r}")

    # --- analysis_payload list -> string join ---
    r7 = format_job({
        "job_title": "ML Engineer", "company": "Cohere", "url": "https://x.com/7",
        "location": "Remote",
        "analysis_payload": {
            "core_responsibilities": ["Train models", "Deploy pipelines"],
            "required_qualifications": ["Python", "PyTorch"],
            "preferred_qualifications": "CUDA",
        },
    })
    record("analysis_payload list joined with '. '",
           r7["analysis_payload"]["core_responsibilities"] == "Train models. Deploy pipelines",
           f"got: {r7['analysis_payload']['core_responsibilities']!r}")
    record("analysis_payload list required_qualifications joined",
           r7["analysis_payload"]["required_qualifications"] == "Python. PyTorch",
           f"got: {r7['analysis_payload']['required_qualifications']!r}")


def test_validate_unit():
    section("PART 1 — validate unit tests (import mode)")

    # Valid complete dict
    good = {
        "job_title": "AI Engineer",
        "company": "Anthropic",
        "location": "Remote",
        "url": "https://boards.greenhouse.io/anthropic/jobs/99999",
        "pay_salary": None,
        "experience_level": None,
        "analysis_payload": {
            "core_responsibilities": "Build safety evals",
            "required_qualifications": "Python",
            "preferred_qualifications": "PyTorch",
        },
    }
    errors = validate(good)
    record("valid complete dict -> empty error list", errors == [], f"got: {errors}")

    # Missing job_title
    bad_title = {k: v for k, v in good.items() if k != "job_title"}
    errors = validate(bad_title)
    has_err = any("job_title" in e for e in errors)
    record("missing job_title -> error captured", has_err, f"errors: {errors}")

    # Empty analysis_payload.core_responsibilities
    bad_core = {**good, "analysis_payload": {
        **good["analysis_payload"], "core_responsibilities": ""
    }}
    errors = validate(bad_core)
    has_err = any("core_responsibilities" in e for e in errors)
    record("empty core_responsibilities -> error captured", has_err, f"errors: {errors}")

    # None pay_salary -> no error (optional)
    none_salary = {**good, "pay_salary": None}
    errors = validate(none_salary)
    record("None pay_salary -> passes validation", errors == [], f"got: {errors}")

    # analysis_payload sub-field is list (not str) -> error
    list_payload = {**good, "analysis_payload": {
        **good["analysis_payload"], "required_qualifications": ["Python", "PyTorch"]
    }}
    errors = validate(list_payload)
    has_err = any("required_qualifications" in e for e in errors)
    record("list in analysis_payload sub-field -> error captured", has_err, f"errors: {errors}")


def test_write_job_db_unit():
    section("PART 1 — write_job_db unit tests")

    _init_test_db()

    base_job = {
        "url": "https://test.example.com/jobs/unit-test-001",
        "job_title": "AI Engineer",
        "company": "TestCo",
        "location": "Atlanta, GA",
        "work_arrangement": "Hybrid",
        "pay_salary": "$90,000 - $110,000",
        "experience_level": "0-2 years",
        "analysis_payload": {
            "core_responsibilities": "Build models",
            "required_qualifications": "Python",
            "preferred_qualifications": "PyTorch",
        },
    }

    # First write — should succeed
    written = _write_job_test_db(base_job, source="web_search")
    record("first write returns True (new row)", written is True, f"got: {written}")

    # Confirm row exists
    con = sqlite3.connect(TEST_DB_PATH)
    count = con.execute(
        "SELECT COUNT(*) FROM jobs WHERE url = ?",
        (base_job["url"],)
    ).fetchone()[0]
    con.close()
    record("row exists in DB after write", count == 1, f"count: {count}")

    # Duplicate write — INSERT OR IGNORE, count stays 1
    written2 = _write_job_test_db(base_job, source="web_search")
    record("second write returns False (duplicate)", written2 is False, f"got: {written2}")
    con = sqlite3.connect(TEST_DB_PATH)
    count2 = con.execute(
        "SELECT COUNT(*) FROM jobs WHERE url = ?",
        (base_job["url"],)
    ).fetchone()[0]
    con.close()
    record("row count stays 1 after duplicate write", count2 == 1, f"count: {count2}")

    # salary_warning = 1 when pay_salary is None
    null_sal_job = {**base_job,
                    "url": "https://test.example.com/jobs/unit-test-002",
                    "pay_salary": None}
    _write_job_test_db(null_sal_job, source="greenhouse_api")
    con = sqlite3.connect(TEST_DB_PATH)
    sw = con.execute(
        "SELECT salary_warning FROM jobs WHERE url = ?",
        (null_sal_job["url"],)
    ).fetchone()[0]
    con.close()
    record("salary_warning = 1 when pay_salary is None", sw == 1, f"got: {sw}")

    # salary_warning = 0 when pay_salary is present
    con = sqlite3.connect(TEST_DB_PATH)
    sw2 = con.execute(
        "SELECT salary_warning FROM jobs WHERE url = ?",
        (base_job["url"],)
    ).fetchone()[0]
    con.close()
    record("salary_warning = 0 when pay_salary present", sw2 == 0, f"got: {sw2}")


# ---------------------------------------------------------------------------
# PART 2 — Integration Test
# ---------------------------------------------------------------------------

def test_integration_greenhouse():
    section("PART 2 — Integration test (live Greenhouse API)")

    _init_test_db()

    # --- Step 1: Hit Greenhouse API ---
    api_url = "https://boards-api.greenhouse.io/v1/boards/anthropic/jobs"
    print(f"\n  GET {api_url}")

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        record("Greenhouse API reachable", False, str(e))
        print("  Skipping integration test — no network access.")
        return
    except Exception as e:
        record("Greenhouse API parse", False, str(e))
        return

    jobs_list = raw.get("jobs", [])
    record("Greenhouse API returns jobs list",
           isinstance(jobs_list, list) and len(jobs_list) > 0,
           f"count: {len(jobs_list)}")

    if not jobs_list:
        print("  No jobs returned from API — skipping remaining integration steps.")
        return

    first = jobs_list[0]
    job_url = first.get("absolute_url", "")
    job_title_raw = first.get("title", "Untitled")
    job_location = (first.get("location") or {}).get("name", "Unknown")

    print(f"  First job: {job_title_raw!r} — {job_url}")
    _write_log(f"[SCOUT] Found job from Greenhouse API: {job_title_raw} @ Anthropic — {job_url}")

    # --- Step 2: Build job dict and run format -> validate -> write ---
    raw_dict = {
        "url": job_url,
        "job_title": job_title_raw,
        "company": "Anthropic",
        "location": job_location,
        "pay_salary": None,
        "experience_level": None,
        "analysis_payload": {
            "core_responsibilities": f"Role at Anthropic: {job_title_raw}",
            "required_qualifications": "See job posting for full details",
            "preferred_qualifications": "See job posting for full details",
        },
    }

    _write_log(f"[PROCESSOR] Starting job-processor for: {job_url}")

    # Format
    try:
        formatted = format_job(raw_dict)
        _write_log(f"[FORMAT] format_job completed for: {job_url}")
        record("format_job runs without error", True)
    except ValueError as e:
        _write_log(f"[FORMAT FAIL] {job_url} — {e}")
        record("format_job runs without error", False, str(e))
        return

    # Validate
    errors = validate(formatted)
    if errors:
        _write_log(f"[GATE FAIL] {job_url} — {errors}")
        record("validate passes on Greenhouse job", False, f"errors: {errors}")
        return
    else:
        _write_log(f"[GATE PASS] {job_url}")
        record("validate passes on Greenhouse job", True)

    # Write to test DB
    written = _write_job_test_db(formatted, source="greenhouse_api")
    if written:
        _write_log(f"[WRITTEN] {job_url} — {formatted['job_title']} @ {formatted['company']}")
    else:
        _write_log(f"[DUPLICATE] {job_url}")
    record("job written to test_scout.db", written is True, f"returned: {written}")

    # --- Step 3: Print results table ---
    print(f"\n  Results table (.tmp/{USER_ID}/test_scout.db):\n")

    con = sqlite3.connect(TEST_DB_PATH)
    con.row_factory = sqlite3.Row
    rows = con.execute("""
        SELECT job_title, company, location, work_arrangement,
               pay_salary, experience_level, source, status, salary_warning
        FROM jobs
        ORDER BY discovered_at DESC
        LIMIT 10
    """).fetchall()
    con.close()

    if not rows:
        print("  (no rows)")
        return

    col_names = ["job_title", "company", "location", "work_arrangement",
                 "pay_salary", "experience_level", "source", "status", "salary_warning"]
    col_widths = [max(len(c), max((len(str(r[c] or "")) for r in rows), default=0))
                  for c in col_names]

    header = "  " + "  ".join(c.ljust(w) for c, w in zip(col_names, col_widths))
    divider = "  " + "  ".join("-" * w for w in col_widths)
    print(header)
    print(divider)
    for row in rows:
        line = "  " + "  ".join(
            str(row[c] if row[c] is not None else "").ljust(w)
            for c, w in zip(col_names, col_widths)
        )
        print(line)


# ---------------------------------------------------------------------------
# PART 3 — Log Validation
# ---------------------------------------------------------------------------

def test_log_validation():
    section("PART 3 — Log file validation")

    print(f"  Log: {LOG_PATH}\n")

    if not os.path.exists(LOG_PATH):
        record("Log file exists", False, f"not found: {LOG_PATH}")
        return

    record("Log file exists", True)

    with open(LOG_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    print(f"  --- log contents ---")
    for line in content.strip().splitlines():
        print(f"  {line}")
    print()

    checks = [
        ("[SCOUT]",     "[SCOUT] marker present"),
        ("[PROCESSOR]", "[PROCESSOR] marker present"),
        ("[FORMAT]",    "[FORMAT] marker present"),
    ]
    gate_check = ("[GATE PASS]" in content or "[GATE FAIL]" in content,
                  "[GATE PASS] or [GATE FAIL] present")
    db_check = (
        "[WRITTEN]" in content or "[DUPLICATE]" in content or "[FILTERED]" in content,
        "[WRITTEN] or [DUPLICATE] or [FILTERED] present",
    )

    for marker, label in checks:
        record(label, marker in content)
    record(gate_check[1], gate_check[0])
    record(db_check[1], db_check[0])


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def print_summary():
    section("SUMMARY")
    total = len(results)
    passed = sum(1 for _, ok, _ in results if ok)
    failed = total - passed

    for label, ok, detail in results:
        status = PASS if ok else FAIL
        suffix = f" — {detail}" if detail and not ok else ""
        print(f"  [{status}] {label}{suffix}")

    print(f"\n  {passed}/{total} passed", end="")
    if failed:
        print(f"  |  {failed} FAILED")
    else:
        print("  — all clear")

    return failed == 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\nJobSearchToolAgentic — Scout Pipeline Test Suite")
    print(f"Run at: {datetime.now(timezone.utc).isoformat()}")

    test_format_job_unit()
    test_validate_unit()
    test_write_job_db_unit()
    test_integration_greenhouse()
    test_log_validation()

    ok = print_summary()
    sys.exit(0 if ok else 1)
