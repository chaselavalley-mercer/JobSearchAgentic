# 📋 Directive: Job Pipeline Orchestrator
**Version**: 1.0 | **Layer**: 1 (Directive)
**Triggered by**: `/apply [URL]` workflow in `.agent/workflows/apply.md`

---

## Overview

This directive is the single source of truth (SOP) for the full job application pipeline. It is executed by the orchestration layer (you) in response to a `/apply [URL]` command. It does not auto-apply to jobs. Its output is a tailored, audited `.docx` resume and a structured log entry.

**Input**: A URL pointing to a live job posting.
**Output**:
- `.users/{user_id}/{user_id}_{job_title}_{company}.docx`
- `logs/{user_id}/{YYYY-MM-DD}_{company}.log`

**Python Interpreter**: All `python` calls in this directive MUST use the absolute path below, wrapped in PowerShell single quotes to handle spaces:
```
'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe'
```

**User ID**: Default is `chase_lavalley`. Resolve from `.users/` directory if multiple users exist.

---

## Pre-Flight Checklist

Before starting any phase, confirm:
- [ ] `.env` exists and is non-empty (contains at least `PYTHON_PATH` and `USER_ID`)
- [ ] `.users/{user_id}/knowledge.md` exists
- [ ] `directives/global_master.docx` exists
- [ ] `logs/{user_id}/` directory exists (create it if not: `New-Item -ItemType Directory -Force`)
- [ ] `.tmp/{user_id}/` directory exists (create it if not)

---

## Phase 1: Data — Scrape & Validate

**Goal**: Produce a verified, schema-compliant JSON snapshot of the target job posting.

### Step 1.1 — Scrape

Invoke the `job-scraper` skill with the provided URL:
- **user_id**: `{user_id}`
- **url**: `{url}`
- The skill will save raw output to `.tmp/{user_id}/scraped_jobs.json`.

After the skill runs, copy/rename the single-job result to:
```
.tmp/{user_id}/current_job.json
```

The `current_job.json` file MUST contain these top-level keys:
```json
{
  "job_title": "string",
  "company": "string",
  "location": "string",
  "url": "string",
  "pay_salary": "string or null",
  "experience_level": "string or null",
  "analysis_payload": {
    "core_responsibilities": "string",
    "required_qualifications": "string",
    "preferred_qualifications": "string"
  }
}
```

### Step 1.2 — Schema Gate (EXECUTION GATE — DO NOT SKIP)

Run the validation script. Phase 2 is blocked until this exits 0.

```powershell
& 'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe' execution/validate_job.py .tmp/{user_id}/current_job.json
```

- **Exit 0**: Proceed to Phase 2.
- **Exit 1**: Parse the printed missing fields, correct `current_job.json` manually or re-scrape, then re-run the gate. DO NOT proceed until exit 0.

---

## Phase 2: Analysis — Ranked Content Selection

**Goal**: Use the career-architect skill to perform a gap analysis and produce a ranked, slot-keyed content mapping for the resume.

### Step 2.1 — Career Architect

Invoke the `career-architect` skill with:
- **user_id**: `{user_id}`
- **knowledge_path**: `.users/{user_id}/knowledge.md`
- **job_data**: contents of `.tmp/{user_id}/current_job.json`

The skill performs:
1. **Asymmetric Gap Analysis**: Scores every Experience and Project in `knowledge.md` against the JD's `analysis_payload`.
2. **Ranked Selection**:
   - **Top 3 Experiences**: Ranked by relevance score. The most recent and university experiences get a +10% priority boost per the resume builder rules.
   - **Top 3 Projects**: Ranked by relevance score.
3. **Slot Mapping**: Outputs a JSON object keyed by the actual placeholder names extracted from `directives/global_master.docx` (pattern: `[Slot_...]` mixed-case and `[Work_Dates_N]` for dates).

### Step 2.2 — Save Analysis Output

Save the ranked mapping to:
```
.tmp/{user_id}/career_analysis.json
```

This file feeds directly into Phase 3.

### Edge Cases
- If fewer than 3 Experiences or Projects exist in `knowledge.md`, provide `""` for the remaining slots — the assembler will collapse those sections.
- If a 3rd Experience/Project scores below 0.6, omit it now rather than triggering the Trim Loop later.

---

## Phase 3: Execution — Resume Assembly

**Goal**: Generate a tailored, page-optimized `.docx` resume. Target: **~1.25 pages**. Hard ceiling: **1.5 pages**.

### Step 3.1 — Merge Analysis + Resume Args

Invoke the `resume_builder` skill with:
- **user_id**: `{user_id}`
- **career_analysis**: `.tmp/{user_id}/career_analysis.json`
- **template**: `directives/global_master.docx`
- The skill merges career_analysis into a full `resume_args.json` covering ALL slots in the template.

Save the final slot mapping to:
```
.tmp/{user_id}/resume_args.json
```

### Step 3.2 — Assemble Document

```powershell
& 'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe' execution/docx_assembler.py `
  --template directives/global_master.docx `
  --mapping .tmp/{user_id}/resume_args.json `
  --output .users/{user_id}/{user_id}_{job_title}_{company}.docx
```

**Exit codes**:
- **Exit 0**: Document assembled within page limit. Proceed to Phase 4.
- **Exit 2 (TRIM_REQUIRED)**: Document exceeds 1.5 pages. Invoke the Trim Loop below.
- **Exit 1**: Fatal error. Read the stderr output, fix the cause (missing file, bad JSON, etc.), and re-run.

### Step 3.3 — Trim Loop (if TRIM_REQUIRED)

Execute the following steps exactly once per loop iteration. Maximum 2 iterations before escalating to user.

1. **Identify the lowest-ranked project** in `.tmp/{user_id}/career_analysis.json` (sort by score ascending).
2. **Null its slots** in `resume_args.json`: assign `""` to all `[Slot_...]` / `[Project_...]` keys belonging to that project.
3. **Re-run Step 3.2**.
4. If still exit 2 after 2 iterations: **stop and surface to user** with the current `.docx` and a note to manually trim.

### Step 3.99 — Residual Slot Check (MANDATORY — DO NOT SKIP)

After every successful assembly (exit 0 or 2), scan the output `.docx` for unreplaced placeholders. A `"Success:"` message alone is **not** sufficient — the script saves even if zero replacements were made.

```powershell
& 'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe' -c "
import zipfile, re, sys
path = sys.argv[1]
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml').decode('utf-8')
text = re.sub(r'<[^>]+>', '', xml)
slots = re.findall(r'\\[[A-Za-z][A-Za-z0-9_]+\\]', text)
if slots:
    print('UNREPLACED SLOTS FOUND:')
    for s in sorted(set(slots)): print(f'  {s}')
    sys.exit(1)
else:
    print('CLEAN - no unreplaced slots.')
    sys.exit(0)
" ".users/{user_id}/{output_filename}.docx"
```

- **Exit 0 / prints CLEAN**: proceed to Phase 4.
- **Exit 1 / prints UNREPLACED SLOTS**: add the missing keys to `resume_args.json` and re-run Step 3.2.

---

## Phase 4: Audit — Hallucination Check & Logging

**Goal**: Verify the final document contains no fabricated claims and log the pipeline's final state.

### Step 4.1 — Run Audit

```powershell
& 'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe' execution/audit_resume.py `
  --docx .users/{user_id}/{user_id}_{job_title}_{company}.docx `
  --knowledge .users/{user_id}/knowledge.md `
  --log-dir logs/{user_id}/
```

The audit script will:
- Extract all text from the final `.docx`.
- Flag any bullet point that contains a company name, technology, or metric **not present** in `knowledge.md`.
- Write a structured log to `logs/{user_id}/{YYYY-MM-DD}_{company}.log`.

### Step 4.2 — Review Audit Output

- **PASS**: All bullets are traceable to `knowledge.md`. Pipeline complete. Surface the `.docx` path to the user.
- **FAIL**: Read the flagged bullets in the log. Correct them in `resume_args.json` and re-run Step 3.2 (no need to re-run Phase 1 or 2). Then re-run the audit.

---

## Error Recovery (Self-Annealing)

| Error | Action |
|-------|--------|
| Schema gate exits 1 | Fix `current_job.json` or re-scrape. Re-run the gate. |
| `docx_assembler.py` exits 1 | Read stderr. Check template path, JSON validity, and Python path. |
| Trim Loop exhausted (2 iters) | Surface to user with current `.docx` for manual trim. |
| Audit FAIL | Correct flagged bullets in `resume_args.json`. Re-run assembler + audit. |
| Any `FileNotFoundError` | Ensure pre-flight directories exist. Re-run failed step. |

---

## Learnings & Updates

*Last updated: 2026-03-11*

- Python 3.11 must be referenced by absolute path on this machine to bypass venv and PATH resolution issues. Use `'C:\Users\cal-asus1\AppData\Local\Programs\Python\Python311\python.exe'` in all PowerShell calls.
- All intermediate files live in `.tmp/` — never commit, always regeneratable.
- The `docx_assembler.py` script delegates actual paragraph surgery to `remodel_docx.py`; keep them separate.
- Page-count estimation is approximate (word-count heuristic). If it disagrees with Word's actual render, trust the rendered output and trigger trim manually.
- **[2026-03-11 BUG FIX]** `remodel_docx.py` line 116 had a case-sensitive regex `\[SLOT_...\]` that never matched the template's actual placeholders (`[Slot_...]` mixed-case, `[Work_Dates_N]` with no prefix). Fixed to `\[[A-Za-z][A-Za-z0-9_]+\]`. Always run Step 3.99 (residual slot scan) after assembly to catch this class of silent failure.
- **Template slot naming convention**: `global_master.docx` uses `[Slot_Work_Company_1]` (capital S, lowercase lot) and `[Work_Dates_1]` (no Slot_ prefix). JSON keys in `resume_args.json` must omit the outer brackets: `"Slot_Work_Company_1": "value"`.
