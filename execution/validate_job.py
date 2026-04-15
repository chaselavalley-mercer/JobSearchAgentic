"""
validate_job.py — Transport-Agnostic Schema Validator
Layer: 3 (Execution)
Usage:
  CLI:    python execution/validate_job.py <path_to_json>
  Import: from execution.validate_job import validate

CLI mode preserves backward compatibility with job_pipeline_orchestrator.md.
Import mode returns List[str] of errors — empty list = valid — with no side
effects and no sys.exit(), safe for parallel subagent use.
"""

import json
import os
import sys


# ---------------------------------------------------------------------------
# Self-Source: load .env from project root
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


# ---------------------------------------------------------------------------
# Schema definition
# ---------------------------------------------------------------------------
REQUIRED_TOP_LEVEL = ["job_title", "company", "location", "url", "analysis_payload"]

REQUIRED_ANALYSIS_PAYLOAD = [
    "core_responsibilities",
    "required_qualifications",
    "preferred_qualifications",
]

# Optional fields — allowed to be None; never raise an error for these
OPTIONAL_TOP_LEVEL = ["pay_salary", "experience_level", "work_arrangement"]


# ---------------------------------------------------------------------------
# Core validate() — single source of truth
# ---------------------------------------------------------------------------

def validate(data: dict) -> list[str]:
    """
    Validate the shape of a job dict.

    Returns a list of human-readable error strings.
    An empty list means the dict is valid and ready for the pipeline.

    This function has no side effects: no file I/O, no printing, no sys.exit().
    """
    errors = []

    if not isinstance(data, dict):
        return ["Root value must be an object (dict)."]

    for field in REQUIRED_TOP_LEVEL:
        if field not in data:
            errors.append(f"Missing required top-level field: '{field}'")
            continue
        if field == "analysis_payload":
            continue  # validated separately below
        value = data[field]
        if not isinstance(value, str):
            errors.append(f"Field '{field}' must be a string, got: {type(value).__name__}")
        elif value.strip() == "":
            errors.append(f"Field '{field}' must not be empty.")

    if "analysis_payload" in data:
        payload = data["analysis_payload"]
        if not isinstance(payload, dict):
            errors.append("Field 'analysis_payload' must be an object (dict).")
        else:
            for sub in REQUIRED_ANALYSIS_PAYLOAD:
                if sub not in payload:
                    errors.append(f"Missing required field: 'analysis_payload.{sub}'")
                    continue
                value = payload[sub]
                if not isinstance(value, str):
                    errors.append(
                        f"Field 'analysis_payload.{sub}' must be a string, "
                        f"got: {type(value).__name__}"
                    )
                elif value.strip() == "":
                    errors.append(f"Field 'analysis_payload.{sub}' must not be empty.")

    return errors


# ---------------------------------------------------------------------------
# CLI wrapper — preserves backward compatibility
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) != 2:
        print("Usage: python execution/validate_job.py <path_to_json>")
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
