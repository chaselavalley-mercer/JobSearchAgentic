# JobSearchToolAgentic — Claude Operating Guide

## Core Purpose
An agentic job search pipeline for Chase LaValley. Scrapes job postings, evaluates them against a professional profile, and generates tailored resumes. Claude acts as the **Orchestration Layer** between human intent and deterministic Python execution.

---

## Architecture: DOE (Directive → Orchestration → Execution)

| Layer | Description | Location |
|---|---|---|
| **Layer 1 — Directive** | SOPs and workflow definitions | `directives/`, `.agent/workflows/` |
| **Layer 2 — Orchestration** | Claude (reads directives, calls skills, handles errors) | — |
| **Layer 3 — Execution** | Deterministic Python scripts | `execution/` |

---

## Python Environment

Always resolve the Python path from `.env` before execution:

```powershell
$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
```

---

## Command Routing

When a slash command is entered, read the corresponding workflow file and follow it exactly.

| Command | Workflow | Skills Invoked |
|---|---|---|
| `/evaluate [URL]` | `.agent/workflows/evaluate.md` | `job-scraper`, `career-architect` |
| `/apply [URL]` | `.agent/workflows/apply.md` | `job-scraper`, `career-architect`, `resume_builder` |
| `/onboard` | `.agent/skills/user-onboarding/user-onboarding.md` | `user-onboarding` |

---

## Skill & Script Index

### Core Skills (`.agent/skills/`)
- **`job-scraper`** — Playwright fetching and structured JSON extraction
- **`career-architect`** — Single source of truth for evaluation scoring and gate-pass logic
- **`resume_builder`** — Template slot mapping for resume generation

### Execution Scripts (`execution/`)
- **`validate_job_json.py`** — Schema validation gate
- **`docx_assembler.py` / `remodel_docx.py`** — Resume template filling and paragraph-level surgery
- **`audit_resume.py`** — Verifies all bullets against `knowledge.md`

---

## Key Constraints (Never Violate)

- **Source of Truth** — All resume content must be traceable to `.users/chase_lavalley/knowledge.md`
- **Project Privacy** — This job search tool is intentionally excluded from the professional resume
- **Data Integrity** — Never fabricate field values; use `null` for missing data
- **Field Formatting** — `benefits` must always be an array `[]`, never `null`
- **Security** — Only scrape domains listed in `browserAllowlist.txt`
- **Functional Separation** — `career-architect` is for evaluation only; never generate resume bullets during the evaluation phase
- **Post-Process** — Run Step 3.99 (residual slot scan) after every `.docx` assembly
- **File Hygiene** — All intermediates go in `.tmp/chase_lavalley/`; never commit this directory

---

## Self-Annealing Protocol

1. **Identify** — Determine which phase failed: scrape, extraction, scoring, or assembly
2. **Fix** — Correct only the specific script or skill file involved
3. **Resume** — Re-run only the failed step; do not restart the entire pipeline
4. **Update** — Record the lesson in the relevant skill file to prevent recurrence