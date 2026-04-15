# Skill: job-processor
**Layer**: 1 (Directive) → executed by Orchestration layer  
**Scope**: Isolated subagent. One instance per URL. No shared intermediate files.  
**Invoked by**: `directives/job_scout_orchestrator.md`

---

## Input
```json
{
  "url": "<job posting URL>",
  "user_id": "chase_lavalley"
}
```

---

## Pipeline

### Step 1 — Playwright Fetch (stealth config)

Launch a Playwright browser with:
- User agent: `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36`
- Viewport: `1920 × 1080`
- Wait condition: `networkidle`
- Post-load pause: `2 seconds`

Navigate to `{url}`. Extract:
- `document.body.innerText` — full visible text
- All `href` links matching `/jobs/`, `/roles/`, `/careers/`, `/positions/` — for context only, do not crawl further

Store raw text in memory. Do NOT write to any file.

### Step 2 — Structured Extraction

Pass raw text to `scrape_jobs.py`:
```bash
python .agent/skills/job-scraper/scripts/scrape_jobs.py --url {url} --user {user_id}
```

Hold the resulting dict in memory. Do NOT write to `scraped_jobs.json` or `current_job.json`. This subagent is stateless with respect to shared intermediates.

### Step 3 — Format

```python
from execution.format_job import format_job
formatted = format_job(raw_dict)
```

If `format_job` raises `ValueError`, log `[FORMAT FAIL] {url} — {error}` to `logs/{user_id}/scout_{YYYY-MM-DD}.log` and exit this subagent.

### Step 4 — Validate

```python
from execution.validate_job import validate
errors = validate(formatted)
```

If `errors` is non-empty:
- Log `[GATE FAIL] {url} — {errors}` to `logs/{user_id}/scout_{YYYY-MM-DD}.log`
- Exit this subagent. Do not proceed.

### Step 5 — Elimination Filters

Read `.users/{user_id}/search_settings.md`. Apply hard filters in order:

1. **seniority_blocklist**: if `formatted["job_title"]` contains any blocklisted term (case-insensitive) → `[FILTERED] seniority`
2. **experience_max_years**: parse `formatted["experience_level"]`. If minimum years required exceeds `experience_max_years` → `[FILTERED] experience`
3. **min_salary_floor**: if `pay_salary` is not None and the lower bound of the range is below `min_salary_floor` → `[FILTERED] salary`. A `null` `pay_salary` **passes** this filter (salary_warning will be set).
4. **location_whitelist**: if `formatted["location"]` is not None and does not match any entry in `location_whitelist` (substring match, case-insensitive) → `[FILTERED] location`

If any filter triggers: log `[FILTERED] {url} — {reason}` and exit.

### Step 6 — Write to DB

```python
from execution.write_job_db import write_job
write_job(formatted, source="{source}", user_id="{user_id}")
```

`source` is passed in from the scout orchestrator (e.g. `"linkedin_alert"`, `"greenhouse_api"`, `"playwright"`, `"web_search"`).

Log result: `[WRITTEN]` or `[DUPLICATE]` (write_job prints this automatically).

---

## Log Format

All log entries go to `logs/{user_id}/scout_{YYYY-MM-DD}.log`:
```
[WRITTEN]   https://example.com/job/123 — AI Engineer @ Anthropic
[FILTERED]  https://example.com/job/456 — seniority (Senior ML Engineer)
[GATE FAIL] https://example.com/job/789 — Missing required field: 'company'
[FORMAT FAIL] https://example.com/job/000 — Cannot normalize location
```

---

## Constraints

- No shared file writes — intermediates stay in memory
- Fully isolated — one subagent per URL, no cross-subagent state
- No re-crawling — if Playwright fails, log `[SCRAPE FAIL]` and exit
