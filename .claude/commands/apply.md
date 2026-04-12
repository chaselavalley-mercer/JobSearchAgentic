---
description: Apply to a single job posting. Usage - /apply [URL]
---

# /apply [URL]

Triggers the full job application pipeline for a single posting. All logic lives in `directives/job_pipeline_orchestrator.md`. This workflow is a thin trigger only — it parses arguments, initializes directories, and hands off.

## Parameters
- **`URL`** (Required): Full URL to the job posting (e.g., `https://boards.greenhouse.io/company/jobs/12345`).
- **`user_id`** (Optional, default: `chase_lavalley`): The user profile to apply against. Resolves from `.users/` if not specified.

## Steps

### 1. Parse Input
Extract URL from the command. Confirm it is a valid http/https URL. If not, stop and ask the user for a valid URL.

### 2. Resolve User
Set `user_id = chase_lavalley` unless the user specifies otherwise or multiple directories exist in `.users/`.

### 3. Initialize Directories

// turbo
```powershell
New-Item -ItemType Directory -Force -Path ".tmp/chase_lavalley"
New-Item -ItemType Directory -Force -Path "logs/chase_lavalley"
```

### 4. Log Pipeline Start
Append a start entry to `logs/{user_id}/session.log`:
```
[{TIMESTAMP}] SESSION START | URL: {URL} | user_id: {user_id}
```

You may create this log file inline — no script needed for this step.

### 5. Hand Off to Orchestrator
Read `directives/job_pipeline_orchestrator.md` and execute it top-to-bottom using the resolved `user_id` and `URL` as inputs.

Do not skip or reorder phases. The directive is the authority.

### 6. Surface Results
On successful completion, report to the user:
- ✅ Path to the final `.docx`
- 📋 Path to the audit log
- 🎯 Estimated match score (from Phase 2 career-architect output)
