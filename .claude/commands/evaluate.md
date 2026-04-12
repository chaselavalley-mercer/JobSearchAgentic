---
description: Evaluate a single job posting. Usage - /evaluate [URL]
---

# /evaluate [URL]

Scores a job posting across 8 weighted dimensions and outputs a decision
scorecard. Does not generate a resume. Does not apply.

## Steps
### 0. Resolve Python Path
$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
Verify $pythonPath is non-empty before proceeding.

### 1. Parse Input
Extract URL. Confirm it is a valid http/https URL.
If not valid, stop and ask for a correct URL.

### 2. Resolve User
Set user_id = chase_lavalley unless otherwise specified.

### 3. Initialize Directories
```powershell
New-Item -ItemType Directory -Force -Path ".tmp/chase_lavalley"
```

### 4. Call job-scraper skill
Input: URL + user_id
Output: `.tmp/{user_id}/scraped_jobs.json`

### 5. Call career-architect skill
Input: `.tmp/{user_id}/scraped_jobs.json` + `.users/{user_id}/knowledge.md`
Output: `.tmp/{user_id}/evaluation_card.json` + printed scorecard

### 6. Surface to User
Report:
- ✅ Scorecard printed above
- 📋 Full card saved to `.tmp/{user_id}/evaluation_card.json`
- If recommendation is APPLY: suggest running `/apply {url}` to proceed