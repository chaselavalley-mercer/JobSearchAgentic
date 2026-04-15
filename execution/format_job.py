"""
format_job.py — Deterministic Job Dict Normalizer
Layer: 3 (Execution)
Usage: from execution.format_job import format_job

Takes a raw dict from the scraper and returns a clean dict ready for validation.
No LLM calls. No file I/O. Pure transformation.
"""

import re
from typing import Any


# ---------------------------------------------------------------------------
# Field normalizers
# ---------------------------------------------------------------------------

def _normalize_location(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    # Remove parenthetical work-arrangement hints: "Atlanta, GA (Hybrid)" → "Atlanta, GA"
    s = re.sub(r"\s*\([^)]*\)", "", s).strip()
    # Strip after " - " when it indicates arrangement: "Remote - US Only" → "Remote"
    s = re.sub(r"\s*[-–]\s*(US Only|USA|United States|Anywhere|Worldwide|North America).*",
               "", s, flags=re.IGNORECASE).strip()
    # Trailing comma/semicolon cleanup
    s = s.rstrip(",.;").strip()
    return s if s else None


def _normalize_work_arrangement(raw_location: Any, raw_title: Any, raw_desc: Any) -> str:
    """Infer from all available text. Returns Remote | Hybrid | On-site | Unknown."""
    combined = " ".join(
        str(x) for x in [raw_location, raw_title, raw_desc] if x
    ).lower()

    if re.search(r"\bhybrid\b", combined):
        return "Hybrid"
    if re.search(r"\bremote\b", combined):
        return "Remote"
    if re.search(r"\b(in[- ]office|on[- ]site|onsite|in[- ]person)\b", combined):
        return "On-site"
    return "Unknown"


def _normalize_experience_level(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()

    # Preserve "New Grad" if no year range is present
    new_grad_only = re.match(r"^(new\s*grad(?:uate)?)\s*$", s, re.IGNORECASE)
    if new_grad_only:
        return "New Grad"

    # "New Grad / 0-1 years ..." → "0-1 years"
    year_range = re.search(r"(\d+[-–+]\d*\s*years?|\d+\+?\s*years?)", s, re.IGNORECASE)
    if year_range:
        return year_range.group(1).strip()

    # If no year range found but "New Grad" present, return it
    if re.search(r"new\s*grad", s, re.IGNORECASE):
        return "New Grad"

    return s  # pass through if unrecognizable — caller decides


def _normalize_pay_salary(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()

    # Vague phrases → None
    vague = re.compile(
        r"^(competitive|doe|depending on experience|tbd|to be determined|n/?a|not (disclosed|listed|provided)).*",
        re.IGNORECASE,
    )
    if vague.match(s):
        return None

    # Must contain a dollar amount or currency symbol to be useful
    if not re.search(r"[\$€£]?\d[\d,]+", s):
        return None

    # Extract the numeric salary range and strip trailing context
    # "$120,000 - $160,000/year plus equity" → "$120,000 - $160,000"
    match = re.match(
        r"([\$€£]?[\d,]+(?:\.\d+)?\s*[-–to]+\s*[\$€£]?[\d,]+(?:\.\d+)?|[\$€£]?[\d,]+(?:\.\d+)?)",
        s,
    )
    if match:
        return match.group(1).strip()

    return None


def _normalize_job_title(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    # Strip trailing " - Location" or " (Location)" tags
    s = re.sub(r"\s*[-–]\s*(Remote|Hybrid|On[- ]site|[A-Z]{2,}|New York|NYC|SF|LA|Chicago).*",
               "", s, flags=re.IGNORECASE).strip()
    s = re.sub(r"\s*\([^)]*\)$", "", s).strip()
    return s if s else None


def _normalize_company(raw: Any) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()
    # Strip common legal suffixes
    s = re.sub(
        r",?\s*(Inc\.?|LLC\.?|Corp\.?|Ltd\.?|L\.P\.?|PBC\.?|Co\.?)$",
        "", s, flags=re.IGNORECASE,
    ).strip()
    return s if s else None


def _join_if_list(value: Any) -> Any:
    """If value is a list, join with '. ' to produce a single string."""
    if isinstance(value, list):
        return ". ".join(str(item) for item in value if item)
    return value


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def format_job(raw: dict) -> dict:
    """
    Normalize a raw scraper dict.

    Returns a cleaned dict ready for validate_job.validate().
    Raises ValueError if a required field cannot be resolved.
    """
    if not isinstance(raw, dict):
        raise ValueError("format_job expects a dict, got: " + type(raw).__name__)

    out = dict(raw)  # shallow copy — we'll overwrite individual keys

    # --- job_title ---
    out["job_title"] = _normalize_job_title(raw.get("job_title"))
    if not out["job_title"]:
        raise ValueError("Cannot normalize job_title: source value was empty or missing.")

    # --- company ---
    out["company"] = _normalize_company(raw.get("company"))
    if not out["company"]:
        raise ValueError("Cannot normalize company: source value was empty or missing.")

    # --- location ---
    out["location"] = _normalize_location(raw.get("location"))
    if not out["location"]:
        raise ValueError("Cannot normalize location: source value was empty or missing.")

    # --- work_arrangement (inferred from location + title + description text) ---
    raw_desc = ""
    if isinstance(raw.get("analysis_payload"), dict):
        raw_desc = " ".join(
            str(v) for v in raw["analysis_payload"].values() if v
        )
    out["work_arrangement"] = _normalize_work_arrangement(
        raw.get("location"), raw.get("job_title"), raw_desc
    )

    # --- experience_level ---
    out["experience_level"] = _normalize_experience_level(raw.get("experience_level"))

    # --- pay_salary ---
    out["pay_salary"] = _normalize_pay_salary(raw.get("pay_salary"))

    # --- analysis_payload: join list fields into strings ---
    payload = raw.get("analysis_payload")
    if isinstance(payload, dict):
        out["analysis_payload"] = {k: _join_if_list(v) for k, v in payload.items()}

    return out
