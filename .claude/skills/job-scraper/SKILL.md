---
name: job-scraper
description: >
  Activates when the user wants to scrape a job posting URL and extract
  structured data including compensation, benefits, application count,
  work arrangement, and experience requirements.
---

# Job Scraper Skill

**Layer**: 2 (Orchestration)
**Input**: A job posting URL + user_id
**Output**: `.tmp/{user_id}/scraped_jobs.json` — structured job object



---

## Pre-Step — URL Routing

Before running the Playwright scraper, check the URL domain:

- **linkedin.com** → Do NOT call `scrape_jobs.py`. Use the browser tool 
  directly (`browser_navigate` + `browser_snapshot`) to fetch the page 
  content. Claude Code's browser tool has access to your real session 
  cookies and can read authenticated LinkedIn pages.

- **All other domains** (greenhouse.io, lever.co, etc.) → Proceed to 
  Step 1 as normal, calling `scrape_jobs.py`.

## Step 1 — Run Playwright Scraper

$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
& $pythonPath .agent/skills/job-scraper/scripts/scrape_jobs.py --url {url} --user {user_id}

This writes raw page text to `.tmp/{user_id}/raw_job.txt`.

If this fails (empty output, timeout, bot block):
- Retry once with a 5 second delay
- If still failing, log to `.tmp/{user_id}/scrape_errors.log` and stop
- Do NOT proceed to extraction on empty content

---

## Step 2 — Extract Structured Fields

Read `.tmp/{user_id}/raw_job.txt` and extract the following fields.
You are the extractor — no API call needed.

### Required Fields (must be present for schema gate to pass)
| Field | Instructions |
|---|---|
| `title` | Official job title |
| `company` | Hiring company name |
| `location` | City/State or "Remote" |
| `url` | Source URL from top of raw_job.txt |
| `experience_level` | Look for years required, "entry level", "new grad", "0-2 years" etc. If not stated, infer from title and responsibilities |

### Optional Fields (extract if present, null if not — never default to zero)
| Field | Instructions |
|---|---|
| `pay_salary` | Any salary range, hourly rate, or compensation mention. null if not found |
| `work_arrangement` | "Remote", "Hybrid", "On-site", or null if not stated |
| `application_count` | Look for "X applicants", "X people clicked apply", LinkedIn applicant counts. null if not found |
| `benefits` | Extract as array. Look for: medical, dental, vision, 401k, 401k_matching, tuition_reimbursement, PTO, equity, parental_leave, HSA, FSA. Empty array [] if none found — do NOT null this field |
| `posted_date` | Any "posted X days ago", "reposted", or date string. null if not found |

### Analysis Payload (always required)
Extract into three arrays:
```json
"analysis_payload": {
    "core_responsibilities": ["string", "..."],
    "basic_qualifications": ["string", "..."],
    "preferred_qualifications": ["string", "..."]
}
```

---

## Step 3 — Write Output

Save the complete structured object to:
.tmp/{user_id}/scraped_jobs.json

Use this exact schema:
```json
{
  "title": "string",
  "company": "string",
  "location": "string",
  "url": "string",
  "experience_level": "string or null",
  "pay_salary": "string or null",
  "work_arrangement": "string or null",
  "application_count": "number or null",
  "benefits": ["string"],
  "posted_date": "string or null",
  "analysis_payload": {
    "core_responsibilities": ["string"],
    "basic_qualifications": ["string"],
    "preferred_qualifications": ["string"]
  }
}
```

---

## Constraints
- Only visit domains in `browserAllowlist.txt`
- Never invent field values — null is always correct over a guess
- `benefits` is always an array, never null
- Raw text file is a scratchpad — do not surface it to the user