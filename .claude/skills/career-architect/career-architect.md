---
name: career-architect
description: >
  Activates when the user wants to evaluate a job against their profile.
  Performs gate-pass checks, scores across 8 weighted dimensions, and
  outputs a structured evaluation scorecard. Does NOT write resume content.
---

# Career Architect Skill — Evaluation Mode

**Layer**: 2 (Analysis)
**Input**:
  - `.tmp/{user_id}/scraped_jobs.json` — structured job data
  - `.users/{user_id}/knowledge.md` — user's skills and experience
**Output**: `.tmp/{user_id}/evaluation_card.json` + printed scorecard

---

## Step 1 — Gate-Pass Check (Binary — No Scoring)

Run these three checks first. If ANY gate fails, stop immediately.
Write the card with `gate_pass.passed: false` and `recommendation: SKIP`.
Do not proceed to scoring.

| Gate | Rule | Fail Condition |
|---|---|---|
| `fits_experience` | Role must be achievable as a new grad | Explicitly requires >2 years experience |
| `fits_role_type` | Must be AI-adjacent | Not in: AI Engineer, ML Engineer, AI Consultant, Agentic, GenAI, AI Solutions, Data Science, AI Product |
| `posted_recently` | Must be fresh | Posted or reposted more than 48 hours ago |

---

## Step 2 — Null Field Check

Before scoring, check which optional fields are present in `scraped_jobs.json`:
- `pay_salary`
- `work_arrangement`
- `application_count`
- `benefits`

For any null field:
- Omit that dimension from scoring entirely
- Add field name to `null_fields` array in the card
- Renormalize remaining weights to sum to 1.0

---

## Step 3 — Score Each Dimension

Read `.users/{user_id}/knowledge.md` before scoring `keyword_match`.
For each present dimension, produce a score (1-5) and a one-line reason.

### Scoring Rubric

**role_substance** (weight: 0.25)
- 5 = Real AI engineering: building models, agents, pipelines, systems
- 3 = Mixed: some AI work, some maintenance or support
- 1 = AI in name only: prompt wrapping, GPT integrations, no engineering depth

**keyword_match** (weight: 0.20)
- Compare `basic_qualifications` + `preferred_qualifications` against skills in `knowledge.md`
- 5 = Meets all or nearly all requirements
- 3 = Meets ~60% of requirements
- 1 = Significant gaps, would need months of ramp-up

**growth_signal** (weight: 0.15)
- 5 = Explicit: mentorship program, career ladder, learning budget, rotation program
- 3 = Implied: fast-growing team, senior engineers present, new product area
- 1 = No signal: maintenance role, legacy system, no team growth mentioned

**compensation** (weight: 0.13)
- null = score 2 (opacity penalty — hiding salary costs candidates time)
- <$60k = 1
- $60k-$74k = 3
- $75k-$89k = 4
- $90k+ = 5

**benefits** (weight: 0.10)
- Score based on count of: medical, dental, vision, 401k_matching, tuition_reimbursement
- 5 = All 5 present
- 4 = 4 present
- 3 = 3 present (or partial list)
- 2 = 1-2 present
- 1 = empty array (none listed)

**location_fit** (weight: 0.12)
- 5 = Atlanta, GA
- 4 = Georgia, Tennessee, or Florida (non-Atlanta)
- 3 = Remote (fully)
- 2 = Other US city
- 1 = Requires relocation outside preference states

**application_count** (weight: 0.03)
- null = omit from scoring
- <20 applicants = 5
- 20-50 = 4
- 50-100 = 3
- >100 = 2
- Note reposts in reason — a repost weakens the penalty slightly

**work_arrangement** (weight: 0.02)
- null = omit from scoring
- Remote = 5
- Hybrid = 4
- On-site with flexibility = 3
- On-site only = 1

---

## Step 4 — Compute Composite Score
composite_score = sum(score[d] * normalized_weight[d])
for all present (non-null) dimensions

Renormalize weights if any dimensions were omitted.
Round to 2 decimal places.

**Grade thresholds:**
- A = 4.5 - 5.0
- B = 4.0 - 4.49
- C = 3.0 - 3.99
- D = below 3.0

**Recommendation logic:**
- All gates passed AND composite >= 4.0 → `APPLY`
- All gates passed AND composite 3.0-3.99 → `REVIEW`
- All gates passed AND composite < 3.0 → `SKIP`
- Any gate failed → `SKIP`

---

## Step 5 — Write Output

Save to `.tmp/{user_id}/evaluation_card.json`:

```json
{
  "job_id": "{company}_{title}_{date}",
  "evaluated_at": "ISO timestamp",

  "job_data": { },

  "gate_pass": {
    "passed": true,
    "gates": {
      "fits_experience": { "passed": true, "reason": "..." },
      "fits_role_type": { "passed": true, "reason": "..." },
      "posted_recently": { "passed": true, "reason": "..." }
    }
  },

  "null_fields": [],

  "scores": {
    "role_substance": { "score": 0, "weight": 0.25, "reason": "..." },
    "keyword_match":  { "score": 0, "weight": 0.20, "reason": "..." },
    "growth_signal":  { "score": 0, "weight": 0.15, "reason": "..." },
    "compensation":   { "score": 0, "weight": 0.13, "reason": "..." },
    "benefits":       { "score": 0, "weight": 0.10, "reason": "..." },
    "location_fit":   { "score": 0, "weight": 0.12, "reason": "..." },
    "application_count": { "score": 0, "weight": 0.03, "reason": "..." },
    "work_arrangement":  { "score": 0, "weight": 0.02, "reason": "..." }
  },

  "composite_score": 0.00,
  "grade": "B",
  "recommendation": "APPLY",

  "decision_card": {
    "title": "...",
    "company": "...",
    "pay": null,
    "composite_score": 0.00,
    "grade": "B",
    "gaps": ["..."]
  }
}
```
### 6. Persist to Database

$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
& $pythonPath .agent/skills/job-scraper/scripts/scrape_jobs.py --url {url} --user {user_id}

- Exit 0: Record saved. Surface scorecard to user.
- Exit 1: evaluation_card.json missing or malformed. Re-run career-architect.
- Exit 2: Database write error. Check .users/{user_id}/ directory exists.
---

## Step 7 — Print Scorecard to User

After writing the file, print this summary directly in the terminal:
╔══════════════════════════════════════════════╗
║  EVALUATION SCORECARD                        ║
╠══════════════════════════════════════════════╣
║  Role    : {title}                           ║
║  Company : {company}                         ║
║  Pay     : {pay_salary or "Not listed"}      ║
║  Score   : {composite_score} / 5.0  [{grade}]║
║  Result  : {recommendation}                  ║
╠══════════════════════════════════════════════╣
║  DIMENSION SCORES                            ║
║  Role Substance   : {score} / 5              ║
║  Keyword Match    : {score} / 5              ║
║  Growth Signal    : {score} / 5              ║
║  Compensation     : {score} / 5              ║
║  Benefits         : {score} / 5              ║
║  Location Fit     : {score} / 5              ║
║  App Volume       : {score} / 5  (or N/A)   ║
║  Work Arrangement : {score} / 5  (or N/A)   ║
╠══════════════════════════════════════════════╣
║  GAPS                                        ║
║  • {gap_1}                                   ║
║  • {gap_2}                                   ║
╚══════════════════════════════════════════════╝

---

## Constraints
- NEVER write resume bullets or slot content — evaluation only
- NEVER auto-apply — recommendation informs the user, user decides
- ALWAYS read knowledge.md before scoring keyword_match
- ALWAYS renormalize weights when dimensions are omitted