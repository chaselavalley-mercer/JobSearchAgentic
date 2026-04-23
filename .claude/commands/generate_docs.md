# Workflow: Generate Documents
**Version**: 1.0 | **Layer**: 1 (Directive)
**Triggered by**: Dashboard "Generate Documents" button → `/api/run` endpoint → `claude -p "/generate-docs {URL}"`

---

## Overview

Thin trigger for the document generation phases of the job pipeline.
Unlike `/apply`, this workflow **assumes the job is already evaluated** — it skips
Phase 1 (scrape) and the gate check if a valid `jobs.db` row already exists for
the URL, going directly to Phases 2–4 (analysis → assembly → audit).

If no evaluated row exists, it falls back to the full `/apply` pipeline.

**Input**: A single job posting URL
**Output**:
- `.users/{user_id}/{user_id}_{job_title}_{company}.docx`
- `logs/{user_id}/{YYYY-MM-DD}_{company}.log`

**User ID**: `chase_lavalley`

---

## Step 1 — Resolve User

Set `user_id = chase_lavalley`.

---

## Step 2 — Initialize Directories

```powershell
New-Item -ItemType Directory -Force -Path ".tmp/chase_lavalley"
New-Item -ItemType Directory -Force -Path "logs/chase_lavalley"
```

---

## Step 3 — Check DB for Existing Evaluated Row

Query `jobs.db` for the provided URL:

```powershell
$pythonPath = (Get-Content .env | Where-Object { $_ -match '^PYTHON_PATH=' }) -replace 'PYTHON_PATH=',''
& $pythonPath -c "
import sqlite3, sys, json
db = '.users/chase_lavalley/jobs.db'
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
row = con.execute('SELECT * FROM evaluations WHERE url = ?', (sys.argv[1],)).fetchone()
con.close()
if row:
    d = dict(row)
    print('FOUND')
    print(d.get('title',''))
    print(d.get('company',''))
    print(d.get('composite_score',''))
else:
    print('NOT_FOUND')
" "{url}"
```

**If FOUND** → Log `[DOC GEN] Skipping scrape — row found for {url}` and jump to Step 5.
**If NOT_FOUND** → Log `[DOC GEN] No evaluated row — running full /apply pipeline` and jump to Step 4.

---

## Step 4 — Fallback: Full Apply Pipeline

Read `directives/job_pipeline_orchestrator.md` and execute it top-to-bottom.
This handles scrape → validate → analyze → assemble → audit.
Stop here when complete — do not continue to Step 5.

---

## Step 5 — Reconstruct current_job.json from DB

Pull the evaluated row from `jobs.db` and write a `current_job.json` so that
Phase 2 (career-architect) has the data it expects:

```powershell
& $pythonPath -c "
import sqlite3, sys, json, os

db = '.users/chase_lavalley/jobs.db'
url = sys.argv[1]
con = sqlite3.connect(db)
con.row_factory = sqlite3.Row
row = dict(con.execute('SELECT * FROM evaluations WHERE url = ?', (url,)).fetchone())
con.close()

scores = json.loads(row.get('scores') or '{}')
responsibilities = scores.get('role_substance', {}).get('reason', '')
qualifications   = scores.get('keyword_match', {}).get('reason', '')

job = {
    'job_title':         row.get('title', ''),
    'company':           row.get('company', ''),
    'location':          row.get('location', ''),
    'url':               row.get('url', ''),
    'pay_salary':        row.get('pay_salary'),
    'experience_level':  row.get('experience_level'),
    'analysis_payload': {
        'core_responsibilities':    responsibilities or 'See job posting.',
        'required_qualifications':  qualifications   or 'See job posting.',
        'preferred_qualifications': 'See job posting for preferred qualifications.',
    }
}

os.makedirs('.tmp/chase_lavalley', exist_ok=True)
with open('.tmp/chase_lavalley/current_job.json', 'w') as f:
    json.dump(job, f, indent=2)
print('[DOC GEN] current_job.json written.')
" "{url}"
```

---

## Step 6 — Phase 2: Career Architect (Gap Analysis)

Invoke the `career-architect` skill with:
- **user_id**: `chase_lavalley`
- **knowledge_path**: `.users/chase_lavalley/knowledge.md`
- **job_data**: contents of `.tmp/chase_lavalley/current_job.json`

Save output to `.tmp/chase_lavalley/career_analysis.json`.

This is the ranked slot mapping. Do not skip it even if the job was already evaluated —
the resume content must be generated fresh each time.

---

## Step 7a — Phase 3a: HTML Resume & Cover Letter Generation

Invoke `.claude/skills/html-resume-builder/SKILL.md` with:
- **career_analysis**: `.tmp/chase_lavalley/career_analysis.json`
- **job_data**: `.tmp/chase_lavalley/current_job.json`
- **knowledge**: `.users/chase_lavalley/knowledge.md`

The skill reads both HTML templates and produces:
- `.tmp/chase_lavalley/resume_tailored.html`
- `.tmp/chase_lavalley/letter_tailored.html`

Do not proceed to Step 7b until both files are confirmed written.

---

## Step 7b — Phase 3b: PDF Conversion

Derive `{job_title}` and `{company}` from `current_job.json`.
Sanitize both for use in filenames: lowercase, spaces → underscores, strip special chars.

Convert the resume:
```powershell
node execution/generate-pdf.mjs `
  .tmp/chase_lavalley/resume_tailored.html `
  ".users/chase_lavalley/chase_lavalley_{job_title}_{company}.pdf" `
  --format=letter
```

Convert the cover letter:
```powershell
node execution/generate-pdf.mjs `
  .tmp/chase_lavalley/letter_tailored.html `
  ".users/chase_lavalley/chase_lavalley_cover_{job_title}_{company}.pdf" `
  --format=letter
```

On error from either command: print the node error, stop, do not continue to Step 8.

---

## Step 8 — Phase 4: Audit

The audit script (`audit_resume.py`) operates on `.docx` files and does not
apply to the HTML/PDF path. Skip this step.

Log: `[AUDIT SKIPPED] HTML/PDF path — audit_resume.py not applicable.`

---

## Step 9 — Surface Results

Print to stdout (captured by the dashboard terminal):

```
[DOC GEN COMPLETE]
  Resume : .users/chase_lavalley/chase_lavalley_{job_title}_{company}.pdf
  Letter : .users/chase_lavalley/chase_lavalley_cover_{job_title}_{company}.pdf
  Score  : {composite_score} [{grade}] — {recommendation}
```

---

## Error Recovery

| Failure | Action |
|---|---|
| DB row not found | Fall back to full /apply pipeline (Step 4) |
| `current_job.json` write fails | Check `.tmp/` dir exists. Retry. |
| `career_analysis.json` missing after skill | Re-invoke career-architect. |
| `docx_assembler.py` exit 1 | Read stderr. Fix file path or JSON issue. Retry Step 7. |
| Audit FAIL | Fix flagged bullets. Re-run Steps 7–8. |
| `knowledge.md` missing | Stop. Print: `[ERROR] knowledge.md not found at .users/chase_lavalley/knowledge.md` |