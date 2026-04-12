
# JobSearchToolAgentic — Claude Operating Guide

## What This Is

An agentic job search pipeline for Chase LaValley. It scrapes job postings,
evaluates them against Chase's profile, and generates tailored resumes.
No auto-apply. No autonomous loops. Claude is the orchestration layer
between human intent and deterministic Python scripts.

---

## Architecture: DOE (Directive, Orchestration, Execution)

| Layer | What it is | Where it lives |
|---|---|---|
| **Layer 1 — Directive** | SOPs written in Markdown | `directives/`, `.agent/workflows/`, `.agent/skills/` |
| **Layer 2 — Orchestration** | You (Claude). Read directives, call skills, handle errors | — |
| **Layer 3 — Execution** | Deterministic Python scripts | `execution/` |

**Core principle**: Don't do manually what a script can do reliably.
Push complexity into Layer 3.

---

## Slash Commands

When the user types a slash command, read the corresponding workflow file
first and follow it exactly. Do not improvise steps not listed there.

### `/evaluate [URL]`
Scores a single job posting across 8 weighted dimensions. Does NOT generate
a resume. Does NOT apply.
- **Workflow**: `.agent/workflows/evaluate.md`
- **Skills called** (in order):
  1. `.agent/skills/job-scraper/SKILL.md`
  2. `.agent/skills/career-architect/career-architect.md`
- **Output**: `.tmp/chase_lavalley/evaluation_card.json` + printed scorecard

### `/apply [URL]`
Full pipeline: scrape → gap analysis → build resume → audit.
- **Workflow**: `.agent/workflows/apply.md`
- **Directive**: `directives/job_pipeline_orchestrator.md`
- **Output**: `.users/chase_lavalley/{user_id}_{job_title}_{company}.docx`

---

## Skills (`.agent/skills/`)

### `job-scraper` → `.agent/skills/job-scraper/SKILL.md`
Runs Playwright to fetch raw page text, then extracts structured JSON.
- Script: `.agent/skills/job-scraper/scripts/scrape_jobs.py`
- Script responsibility: Playwright fetch only. No LLM calls.
- Claude Code responsibility: Read raw_job.txt and extract structured fields.
- Output: `.tmp/{user_id}/scraped_jobs.json`
- Only visits domains in `browserAllowlist.txt`
- Never invent field values — `null` is always correct over a guess
- `benefits` is always an array `[]`, never null

### `career-architect` → `.agent/skills/career-architect/career-architect.md`
Evaluates a scraped job against Chase's profile. Evaluation only.
No resume content. No bullet points.
- Input: `.tmp/{user_id}/scraped_jobs.json` + `.users/{user_id}/knowledge.md`
- Output: `.tmp/{user_id}/evaluation_card.json` + printed scorecard
- Gate-pass checks run first (binary). Fail any gate → SKIP, stop.
- 8 weighted dimensions. Null fields omitted, weights renormalized.

### `resume_builder` → `.agent/skills/resume_builder/resume_builder.md`
Merges career analysis into resume_args.json covering all template slots.
Called by `/apply` only — never by `/evaluate`.

### `user-onboarding` → `.agent/skills/user-onboarding/user-onboarding.md`
Provisions a new user workspace from a PDF resume.

---

## Execution Scripts (`execution/`)

| Script | Purpose | Called by |
|---|---|---|
| `validate_job_json.py` | Schema gate — exits 1 if required fields missing | `/apply` Phase 1 |
| `docx_assembler.py` | Fills template slots in `.docx`; exit 2 = TRIM_REQUIRED | `/apply` Phase 3 |
| `remodel_docx.py` | Paragraph-level surgery, called by assembler | `/apply` Phase 3 |
| `audit_resume.py` | Flags bullets not traceable to `knowledge.md` | `/apply` Phase 4 |

## Python Path
Always read from `.env` → `PYTHON_PATH`. Never hardcode in skill files or directives.
To resolve in PowerShell:
$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
## Evaluation Scoring (8 Dimensions)

Gate-pass checks run first — binary, no scoring needed. Fail any = SKIP.

| Gate | Rule |
|---|---|
| `fits_experience` | Explicitly requires >2 years → SKIP |
| `fits_role_type` | Must be AI-adjacent role → SKIP if not |
| `posted_recently` | Must be posted/reposted within 48 hours → SKIP if older |

Scored dimensions (weights must sum to 1.0; renormalize if fields are null):

| Dimension | Weight | Scoring Notes |
|---|---|---|
| `role_substance` | 0.25 | Real AI engineering vs. prompt wrapping |
| `keyword_match` | 0.20 | Cross-reference against `knowledge.md` stack |
| `growth_signal` | 0.15 | Mentorship, career ladder, learning budget |
| `compensation` | 0.13 | Null = 2 (opacity penalty). <$60k = 1. $90k+ = 5 |
| `location_fit` | 0.12 | Atlanta = 5, GA/TN/FL = 4, Remote = 3, other US = 2 |
| `benefits` | 0.10 | Score by count of: medical, dental, vision, 401k, tuition |
| `application_volume` | 0.03 | <20 = 5, 20-50 = 4, 50-100 = 3, >100 = 2 |
| `work_arrangement` | 0.02 | Remote = 5, Hybrid = 4, On-site = 1 |

Grade thresholds: A = 4.5+, B = 4.0-4.49, C = 3.0-3.99, D = below 3.0
Recommendation: APPLY (>=4.0), REVIEW (3.0-3.99), SKIP (<3.0 or gate fail)

---

## User Profile

**Default user**: `chase_lavalley`

| File | Purpose |
|---|---|
| `.users/chase_lavalley/knowledge.md` | Master skill inventory — source of truth for ALL resume content |
| `.users/chase_lavalley/search_settings.md` | Keywords, filters, thresholds |

**Hard filters** (encoded in gate-pass logic):
- Max experience required: 2 years
- Min salary: $60k
- Target locations: Atlanta (primary), GA, TN, FL, Remote
- Seniority blocklist: Senior, Staff, Lead, Manager, Principal, Director, Head

---

## File Layout

```
.agent/
  skills/
    job-scraper/
      SKILL.md                  ← scraper instructions
      scripts/scrape_jobs.py    ← Playwright fetch only
    career-architect/
      career-architect.md       ← evaluation + scorecard
    resume_builder/
      resume_builder.md
    user-onboarding/
      user-onboarding.md
  workflows/
    evaluate.md                 ← /evaluate entry point
    apply.md                    ← /apply entry point
.users/
  chase_lavalley/               ← profile, knowledge, generated .docx files
.tmp/
  chase_lavalley/               ← all intermediates (never commit)
directives/
  job_pipeline_orchestrator.md  ← /apply SOP
  global_master.docx            ← resume template
execution/                      ← deterministic Python scripts
browserAllowlist.txt            ← approved scraping domains
```

---

## Key Rules (Never Violate These)

- **Never fabricate field values** — `null` is always correct over a guess
- **`benefits` is always an array** — use `[]` if empty, never `null`
- **Always read `knowledge.md`** before scoring `keyword_match`
- **Renormalize weights** when any scoring dimension is omitted
- **`career-architect` is evaluation only** — never write resume bullets there
- **Run Step 3.99** (residual slot scan) after every `.docx` assembly
- **Only visit domains in `browserAllowlist.txt`** during scraping
- **Intermediates in `.tmp/`** — never commit this directory

---

## Self-Annealing Protocol

When something breaks:
1. Read the error and identify which layer failed (scrape, extract, score, assemble)
2. Fix the script or skill file
3. Re-run only the failed step — don't restart the whole pipeline
4. Update the relevant skill file with what you learned

Directives and skill files are living documents. Update them as you learn.