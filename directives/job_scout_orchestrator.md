# Directive: Job Scout Orchestrator
**Version**: 1.0 | **Layer**: 1 (Directive)  
**Triggered by**: `/scout` command

---

## Overview

Thin router. Triggers both scouts in parallel, deduplicates against the existing DB, spawns isolated job-processor subagents for each new URL, and prints a session summary.

**Input**: None (reads config from `.users/{user_id}/search_settings.md`)  
**Output**: New rows in `.tmp/{user_id}/scraped_jobs.db` + printed session summary  
**User ID**: Default is `chase_lavalley`

---

## Pre-Flight Checklist

Before firing any scouts, confirm:
- [ ] `.users/{user_id}/search_settings.md` exists and is non-empty
- [ ] `.tmp/{user_id}/scraped_jobs.db` exists. If not: run `python execution/init_db.py --user {user_id}`
- [ ] `logs/{user_id}/` directory exists. If not: create it.
- [ ] `browserAllowlist.txt` exists

If any check fails, surface the issue to the user and stop. Do not proceed with a broken environment.

---

## Step 1 — Fire Both Scouts in Parallel

Invoke `notification-scout` and `portal-scanner` **simultaneously**. Do not wait for one to complete before starting the other.

- `notification-scout` input: `{user_id, time_window_hours: 24}`
- `portal-scanner` input: `{user_id}`

Collect results from both. Each returns a list of `{url, job_title, company, [location], source}` dicts.

---

## Step 2 — Deduplication Against DB

For every URL returned by either scout, check the database:

```python
import sqlite3
con = sqlite3.connect(".tmp/{user_id}/scraped_jobs.db")
cur = con.cursor()
cur.execute("SELECT COUNT(*) FROM jobs WHERE url = ?", (url,))
exists = cur.fetchone()[0] > 0
con.close()
```

- If `exists = True`: mark as duplicate, skip — do not spawn a subagent.
- If `exists = False`: add to the new-URL queue.

Track counts per scout:
- `notification_found`, `notification_new`, `notification_duplicates`
- `portal_found`, `portal_new`, `portal_duplicates`

---

## Step 3 — Spawn job-processor Subagents

For each URL in the new-URL queue, spawn an isolated `job-processor` subagent with:
```json
{
  "url": "<url>",
  "user_id": "{user_id}",
  "source": "<source from scout result>"
}
```

Subagents may run in parallel. Collect their outcomes:
- `[WRITTEN]` → written count
- `[FILTERED]` → filtered count (with reason)
- `[GATE FAIL]` → validation failure count
- `[FORMAT FAIL]` → format failure count
- `[SCRAPE FAIL]` → scrape failure count

---

## Step 4 — Write Scout Log

After all subagents complete, write one row per scout to `scout_log`:

```python
import sqlite3
from datetime import datetime, timezone

con = sqlite3.connect(".tmp/{user_id}/scraped_jobs.db")
cur = con.cursor()
cur.execute(
    """INSERT INTO scout_log
       (session_at, scout_type, urls_found, urls_new, urls_written, urls_filtered, urls_failed, notes)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
    (
        datetime.now(timezone.utc).isoformat(),
        "notification_scout",   # or "portal_scanner"
        urls_found,
        urls_new,
        urls_written,
        urls_filtered,
        urls_failed,
        notes,                  # comma-joined failure URLs if any
    )
)
con.commit()
con.close()
```

Write one row for `notification_scout` and one row for `portal_scanner`.

---

## Step 5 — Print Session Summary

```
========================================
  SCOUT SESSION COMPLETE
========================================
Notification Scout:
  Found:    {notification_found}
  New:      {notification_new}
  Written:  {notification_written}
  Filtered: {notification_filtered}
  Failed:   {notification_failed}

Portal Scanner:
  Found:    {portal_found}
  New:      {portal_new}
  Written:  {portal_written}
  Filtered: {portal_filtered}
  Failed:   {portal_failed}

Duplicates skipped:   {total_duplicates}
Validation failures:  {total_gate_fails}
Total new leads:      {total_written}
========================================
```

---

## Error Recovery

| Error | Action |
|---|---|
| DB not found at pre-flight | Run init_db.py, then retry |
| Scout returns `[]` | Normal — log zero counts, continue to summary |
| All subagents fail | Print summary with zero written, surface error detail to user |
| scout_log INSERT fails | Log warning to stdout, do not abort — session data is already in `jobs` table |
