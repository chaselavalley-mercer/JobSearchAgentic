# 📋 Directive: Evaluate Job (Subagent SOP)
**Version**: 2.0 | **Layer**: 1 (Directive)
**Triggered by**: `execution/dispatch_evaluate.py` — spawned as a headless `claude -p` subagent

---

## Overview

This directive is executed by a headless Claude subagent with no user interaction.
It receives a single job URL, scrapes it, validates the DB write, scores all
dimensions, and updates the row in `jobs.db`. It stops after evaluation.
Document generation and applying are handled by a separate subagent triggered
manually by the user (HITL checkpoint).

**Input**: A single job posting URL passed via the subagent prompt.
**Output**: One complete, evaluated row in `.users/chase_lavalley/jobs.db`

**Failure behavior**: If any phase fails unrecoverably, update the row in
`jobs.db` with `status = 'failed'` and the error in `notes`. Never exit silently.
If no row exists yet (scrape failed before write), insert a minimal failed row.

**User ID**: `chase_lavalley`

**Python Interpreter**:
```
'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe'
```

---

## Pre-Flight

Before starting, confirm:
- `.users/chase_lavalley/jobs.db` exists. If not, run:
  ```powershell
  & 'C:\Users\cal-asus1\...\python.exe' execution/init_db.py --user chase_lavalley
  ```
- `.users/chase_lavalley/knowledge.md` exists
- `.tmp/chase_lavalley/` directory exists (create if not)

---

## Phase 1: Scrape & Write to DB

### Step 1.1 — Scrape

Invoke the `job-scraper` skill with the provided URL:
- **user_id**: `chase_lavalley`
- **url**: `{url}`

The skill extracts all available fields from the job posting. Do not save any
intermediate JSON files. Pass the extracted data directly to Step 1.2.

Expected fields from scraper:
- `job_title`, `company`, `location`, `url` — required
- `core_responsibilities`, `required_qualifications` — required
- `preferred_qualifications`, `pay_salary`, `experience_level`, `work_arrangement` — nullable

### Step 1.2 — Write Scraped Row to DB

Call `write_job_to_db.py` immediately after scraping, before any evaluation.
Pass all extracted fields. Set `status = 'scraped'`.

```powershell
& 'C:\Users\cal-asus1\...\python.exe' execution/write_job_to_db.py `
  --user chase_lavalley `
  --url "{url}" `
  --job-title "{job_title}" `
  --company "{company}" `
  --location "{location}" `
  --pay-salary "{pay_salary}" `
  --experience-level "{experience_level}" `
  --work-arrangement "{work_arrangement}" `
  --core-responsibilities "{core_responsibilities}" `
  --required-qualifications "{required_qualifications}" `
  --preferred-qualifications "{preferred_qualifications}" `
  --status "scraped"
```

- **Exit 0**: Row written. Proceed to Phase 2.
- **Exit 1**: Scrape or write failed. Log error. Stop.

---

## Phase 2: DB Validation Gate

Query the row back out of `jobs.db` and verify required fields are non-null.
This replaces the old `validate_job_json.py` file-based gate.

```powershell
& 'C:\Users\cal-asus1\...\python.exe' execution/validate_db_row.py `
  --user chase_lavalley `
  --url "{url}"
```

**Non-nullable fields** (gate fails if any of these are null or empty):
- `job_title`
- `company`
- `location`
- `url`
- `core_responsibilities`
- `required_qualifications`

**Acceptable as null** (gate passes regardless):
- `pay_salary`
- `benefits`
- `experience_level`
- `work_arrangement`
- `preferred_qualifications`

- **Exit 0**: Validation passed. Proceed to Phase 3.
- **Exit 1**: Validation failed. Update row: `status = 'failed'`,
  `notes = 'DB validation failed: {missing fields}'`. Stop.

---

## Phase 3: Binary Gate Evaluation

Evaluate all 3 gates using the validated DB row and
`.users/chase_lavalley/search_settings.md`.

Evaluate all 3 gates regardless of individual results — never short-circuit.
Record each result and continue. All 3 results are written to the DB in Phase 5.

### Gate 1 — Experience Requirement
- **Pass (1)**: `experience_level` is null, "Not listed", "New Grad",
  "Entry Level", or ≤ 2 years explicitly stated
- **Fail (0)**: Any explicit requirement > 2 years, or title contains a word
  from `seniority_blocklist` in `search_settings.md`
  (`Senior`, `Staff`, `Lead`, `Manager`, `Principal`, `Director`, `Head`)

### Gate 2 — Role Type
- **Pass (1)**: Role aligns with `target_keywords` in `search_settings.md`
  (`AI Engineer`, `ML Engineer`, `Embedded`, `Computer Engineer`,
  `Hardware Engineer`, `Machine Learning`)
- **Fail (0)**: Pure sales, pure PM, non-technical, or no keyword overlap
  with target roles

### Gate 3 — Posting Recency
- **Pass (1)**: Posting appears active and was listed within the last 30 days
  (infer from page content, timestamps, or posting date if visible)
- **Fail (0)**: Posting is closed, expired, filled, or clearly stale

Set `gates_passed = 1` only if all 3 gates pass. Otherwise `gates_passed = 0`.

---

## Phase 4: Dimension Scoring

Score all 8 dimensions on a **1–10 scale**.
Score all dimensions regardless of gate results — partial data is still
valuable for dashboard filtering and future analysis.

Read `.users/chase_lavalley/knowledge.md` and the DB row for this URL
before scoring.

| Dimension | Column | Weight | Scoring Guidance |
|---|---|---|---|
| Role Substance | `score_role_substance` | 0.25 | Depth of technical work in JD, not just keyword presence |
| Keyword Match | `score_keyword_match` | 0.20 | Overlap between JD requirements and knowledge.md stack |
| Growth Signal | `score_growth_signal` | 0.15 | Evidence of learning path, mentorship, or promotion signals |
| Compensation | `score_compensation` | 0.13 | **Null or opaque salary = hard score of 2. No exceptions.** |
| Location Fit | `score_location_fit` | 0.12 | Match against `location_whitelist` in search_settings.md |
| Benefits | `score_benefits` | 0.10 | Equity, health, 401k, PTO signals present in JD |
| Application Volume | `score_application_volume` | 0.03 | Lower applicant count = higher score. Null = 5 (neutral). |
| Work Arrangement | `score_work_arrangement` | 0.02 | Alignment with remote/hybrid preference |

**Null field rule**: If a dimension cannot be scored due to missing JD data,
exclude it from the weighted average and renormalize remaining weights.
Do not zero-score null fields — that distorts the composite unfairly.

**Composite score formula**:
```
composite_score = sum(score_N × weight_N) / sum(weights of scored dimensions only)
```

---

## Phase 5: Write Evaluation Results to DB

Update the existing row with all gate results, dimension scores, composite
score, and final status.

```powershell
& 'C:\Users\cal-asus1\...\python.exe' execution/write_job_to_db.py `
  --user chase_lavalley `
  --url "{url}" `
  --gate-experience {gate_experience} `
  --gate-role-type {gate_role_type} `
  --gate-posting-recency {gate_posting_recency} `
  --gates-passed {gates_passed} `
  --score-role-substance {score_role_substance} `
  --score-keyword-match {score_keyword_match} `
  --score-growth-signal {score_growth_signal} `
  --score-compensation {score_compensation} `
  --score-location-fit {score_location_fit} `
  --score-benefits {score_benefits} `
  --score-application-volume {score_application_volume} `
  --score-work-arrangement {score_work_arrangement} `
  --composite-score {composite_score} `
  --evaluated-at "{timestamp}" `
  --status "evaluated"
```

- **Exit 0**: Row fully evaluated and written. Subagent exits cleanly.
- **Exit 1**: Log error to stdout (captured by dispatcher). Exit code 1.

---

## HITL Checkpoint — Subagent Stops Here

This subagent's job is complete after Phase 5. It does not generate documents,
does not modify `knowledge.md`, and does not trigger any application workflow.

The user reviews evaluated rows in the dashboard and manually triggers the
next subagent (`/apply`) for any job they choose to pursue.

---

## Failure Protocol

There is no user to ask for help. Follow this strictly:

| Failure point | Action |
|---|---|
| Scraper returns empty or errors | Insert minimal row: `status = 'failed'`, `notes = 'Scraper returned no data'`. Stop. |
| DB write fails (Phase 1) | Print error to stdout. Exit code 1. |
| DB validation fails (Phase 2) | Update row: `status = 'failed'`, `notes = 'Validation: {missing fields}'`. Stop. |
| `knowledge.md` missing | Update row: `status = 'failed'`, `notes = 'knowledge.md not found'`. Stop. |
| Scoring error | Write whatever scores completed. Set `status = 'partial'`, `notes = '{error}'`. |
| Final DB write fails (Phase 5) | Print error to stdout. Exit code 1. |
| Any unhandled exception | Update/insert row: `status = 'failed'`, `notes = '{exception type}: {message}'`. Stop. |

**Never exit silently. Always write a row.**