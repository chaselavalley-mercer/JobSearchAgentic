"""
validate_job_json.py — Phase 1 Schema Gate
Layer: 3 (Execution)
Usage: python execution/validate_job_json.py <path_to_current_job.json>

Exit codes:
  0  — Schema is valid. Pipeline may proceed to Phase 2.
  1  — Schema is invalid. Prints missing/malformed fields. Do NOT proceed.

The script self-sources the project .env via python-dotenv so any future
env-gated validation (e.g. API key presence checks) is already wired in.
"""

import sys
import json
import os

# ---------------------------------------------------------------------------
# Self-Source: load .env from project root before anything else
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=_env_path, override=False)
except ImportError:
    pass  # python-dotenv optional for this script; env vars still readable if set externally

# ---------------------------------------------------------------------------
# Required schema definition
# ---------------------------------------------------------------------------
REQUIRED_TOP_LEVEL = ["job_title", "company", "location", "url", "analysis_payload"]

REQUIRED_ANALYSIS_PAYLOAD = [
    "core_responsibilities",
    "required_qualifications",
    "preferred_qualifications",
]

OPTIONAL_TOP_LEVEL = ["pay_salary", "experience_level"]  # documented but not enforced


def validate(data: dict) -> list[str]:
    """Return a list of human-readable validation error strings. Empty = valid."""
    errors = []

    if not isinstance(data, dict):
        return ["Root JSON value must be an object (dict)."]

    # Check top-level required fields
    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required top-level field: '{field}'")
        elif field != "analysis_payload" and not isinstance(data[field], str):
            errors.append(f"Field '{field}' must be a string, got: {type(data[field]).__name__}")
        elif field != "analysis_payload" and str(data[field]).strip() == "":
            errors.append(f"Field '{field}' must not be empty.")

    # Check analysis_payload structure
    if "analysis_payload" in data:
        payload = data["analysis_payload"]
        if not isinstance(payload, dict):
            errors.append("Field 'analysis_payload' must be an object (dict).")
        else:
            for sub in REQUIRED_ANALYSIS_PAYLOAD:
                if sub not in payload:
                    errors.append(f"Missing required field: 'analysis_payload.{sub}'")
                elif not isinstance(payload[sub], str):
                    errors.append(
                        f"Field 'analysis_payload.{sub}' must be a string, "
                        f"got: {type(payload[sub]).__name__}"
                    )
                elif str(payload[sub]).strip() == "":
                    errors.append(f"Field 'analysis_payload.{sub}' must not be empty.")

    return errors


def main():
    if len(sys.argv) != 2:
        print("Usage: python execution/validate_job_json.py <path_to_current_job.json>")
        sys.exit(1)

    json_path = sys.argv[1]

    if not os.path.exists(json_path):
        print(f"[GATE FAIL] File not found: {json_path}")
        sys.exit(1)

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[GATE FAIL] Invalid JSON — {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[GATE FAIL] Could not read file — {e}")
        sys.exit(1)

    errors = validate(data)

    if errors:
        print("[GATE FAIL] Schema validation failed. Fix the following before proceeding:")
        for i, err in enumerate(errors, 1):
            print(f"  {i}. {err}")
        sys.exit(1)

    # Print a clean summary of what was validated
    print("[GATE PASS] Schema valid.")
    print(f"  Job Title  : {data.get('job_title', '')}")
    print(f"  Company    : {data.get('company', '')}")
    print(f"  Location   : {data.get('location', '')}")
    print(f"  URL        : {data.get('url', '')}")
    print(f"  Pay/Salary : {data.get('pay_salary', 'not provided')}")
    print(f"  Exp Level  : {data.get('experience_level', 'not provided')}")
    print("  analysis_payload keys: " + ", ".join(REQUIRED_ANALYSIS_PAYLOAD))
    sys.exit(0)


if __name__ == "__main__":
    main()
