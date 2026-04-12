---
name: job-evaluator
description: >
  Activates after job-scraper produces scraped_jobs.json. Reads each job,
  runs gate-pass checks, scores across 8 weighted dimensions, and outputs
  evaluation_card.json per job. Does NOT generate resumes. Evaluation only.
---

# Job Evaluator Skill

**Layer**: 2 (Analysis)
**Input**: `.tmp/{user_id}/scraped_jobs.json` (array of scraped job objects)
**Output**: `.tmp/{user_id}/evaluations/{job_id}_card.json` per job
**Triggered by**: `/evaluate` workflow or automatically after scout run

---

## User Scoring Profile

Read `.users/{user_id}/search_settings.md` before scoring.
All thresholds and preferences below are Chase's defaults.
Override with user-specific settings if present.

---

## Step 1 — Gate-Pass Check (Run First, No LLM Needed)

These are binary. Fail any gate → mark `gate_pass.passed: false`, log reason,
skip scoring, write card with recommendation: SKIP. Do not proceed to Step 2.

| Gate | Rule |
|---|---|
| `fits_experience` | Job requires >2 years explicitly stated → FAIL |
| `fits_role_type` | Role must be AI-adjacent (AI Engineer, ML Engineer, AI Consultant, Agentic, GenAI, AI Solutions) → FAIL if not |
| `posted_recently` | Posting or reposting must be within 48 hours → FAIL if older |

---

## Step 2 — Data Completeness Check

Before scoring, check if these fields are present in the scraped data:
- `benefits`
- `application_count`
- `pay_salary`
- `work_arrangement`

If any field is null or missing:
- **Do not default to zero**
- **Omit that dimension from scoring entirely**
- **Log the missing field to `null_fields` array in the card**
- **Renormalize remaining weights to sum to 1.0**

---

## Step 3 — Score Each Dimension (LLM Reasoning Required)

For each dimension, produce a score (1-5) and a one-line reason.
Use the scraped `analysis_payload` and `job_data` fields as your evidence.
Cross-reference against `.users/{user_id}/knowledge.md` for keyword matching.

| Dimension | Weight | Scoring Guide |
|---|---|---|
| `role_substance` | 0.25 | 5 = real AI engineering work. 3 = mixed. 1 = prompt wrapping or maintenance only |
| `keyword_match` | 0.20 | Compare `basic_qualifications` + `preferred_qualifications` against user's stack in `knowledge.md`. 5 = meets all. 3 = meets ~60%. 1 = significant gaps |
| `growth_signal` | 0.15 | 5 = explicit mentorship, career ladder, or learning program. 3 = implied. 1 = no signal |
| `compensation` | 0.13 | Null = 2 (opacity penalty). <$60k = 1. $60-75k = 3. $75-90k = 4. $90k+ = 5 |
| `benefits` | 0.10 | 5 = medical+dental+vision+401k+tuition. 3 = partial. 1 = none listed |
| `location_fit` | 0.12 | 5 = Atlanta. 4 = GA/TN/FL. 3 = remote. 2 = other US. 1 = requires relocation outside preferences |
| `application_volume` | 0.03 | 5 = <20. 4 = 20-50. 3 = 50-100. 2 = 100+. Note reposts in reason field |
| `work_arrangement` | 0.02 | 5 = fully remote. 4 = hybrid. 3 = in-person with flexibility. 1 = in-person only |

---

## Step 4 — Compute Composite Score