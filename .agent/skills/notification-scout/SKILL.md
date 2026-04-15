# Skill: notification-scout
**Layer**: 1 (Directive) → executed by Orchestration layer  
**Purpose**: Harvest job URLs from email alert notifications  
**Invoked by**: `directives/job_scout_orchestrator.md` (in parallel with portal-scanner)

---

## Input
```json
{
  "user_id": "chase_lavalley",
  "time_window_hours": 24
}
```
`time_window_hours` defaults to 24 if not provided.

---

## Output

Returns a list of dicts to the scout orchestrator:
```json
[
  {
    "url": "https://www.linkedin.com/jobs/view/...",
    "job_title": "AI Engineer",
    "company": "Anthropic",
    "source": "linkedin_alert"
  }
]
```

---

## Steps

### Step 1 — Open Email Client

Use the Browser Subagent to open Gmail or Outlook (whichever the user has active). Do not store or log credentials at any point.

### Step 2 — Search for Alert Senders

Search inbox for emails from any of:
- `jobs-listings@linkedin.com`
- `alert@indeed.com`
- `no-reply@glassdoor.com`
- `no-reply@joinhandshake.com`

Filter to emails received within the last `{time_window_hours}` hours.

### Step 3 — Extract Job URLs

For each alert email found:
1. Extract `job_title`, `company`, and direct URL from the email body.
2. If only a "View Job" or "Apply" button is present (no direct URL in text): click through and capture the final resolved URL after redirects settle.
3. Record `{url, job_title, company, source}` where `source` is derived from the sender domain:
   - `jobs-listings@linkedin.com` → `"linkedin_alert"`
   - `alert@indeed.com` → `"linkedin_alert"` (reuse tag; Indeed alerts are similar signal)
   - `no-reply@glassdoor.com` → `"linkedin_alert"`
   - `no-reply@joinhandshake.com` → `"linkedin_alert"`

### Step 4 — Title Pre-Filter

Before returning, apply a fast title-level filter using `.users/{user_id}/search_settings.md`:
- **Include**: title must contain at least one term from `target_keywords` (case-insensitive)
- **Exclude**: title must contain zero terms from `seniority_blocklist` (case-insensitive)

Log filtered-out titles as `[TITLE FILTERED] {title} — {company}` (do not add to output list).

### Step 5 — Return

Return the filtered URL list to the scout orchestrator. Do not write to any file directly — the orchestrator handles deduplication and spawns job-processor subagents.

---

## Anti-Bot Rules

- Maximum **10 navigation actions per domain per session**
- **60-second pause** between processing batches of more than 5 emails
- Never store, log, or transmit credentials or session tokens
- If the browser blocks navigation: log `[ACCESS BLOCKED] {domain}` and skip that sender

---

## Failure Handling

- If no matching emails found: return an empty list `[]` — not an error
- If a redirect URL cannot be resolved after 2 attempts: skip that listing and log `[URL UNRESOLVED] {job_title} @ {company}`
- If inbox access fails entirely: log `[INBOX FAIL] notification-scout aborted` and return `[]`
