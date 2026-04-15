# Skill: portal-scanner
**Layer**: 1 (Directive) → executed by Orchestration layer  
**Purpose**: Discover job URLs by crawling career pages and APIs directly  
**Invoked by**: `directives/job_scout_orchestrator.md` (in parallel with notification-scout)

---

## Input
```json
{
  "user_id": "chase_lavalley"
}
```

---

## Output

Returns a list of dicts to the scout orchestrator:
```json
[
  {
    "url": "https://boards.greenhouse.io/anthropic/jobs/4567890",
    "job_title": "AI Engineer",
    "company": "Anthropic",
    "location": "Remote",
    "source": "greenhouse_api"
  }
]
```

---

## Steps

### Pre-flight

Load `.users/{user_id}/search_settings.md`. Extract:
- `target_keywords`
- `job_boards`
- `greenhouse_slugs`
- `seniority_blocklist`
- `location_whitelist`
- `listing_limit`

---

### Level 1 — Greenhouse API (no browser required)

For each slug in `greenhouse_slugs`:
```
GET https://boards-api.greenhouse.io/v1/boards/{slug}/jobs
```

Parse response JSON. For each job in `jobs[]`:
- Extract `title`, `absolute_url`, `location.name`
- Apply title filter: must match at least one `target_keywords` term AND zero `seniority_blocklist` terms
- If location visible: apply `location_whitelist` filter (substring match, case-insensitive)
- If passes: add `{url: absolute_url, job_title: title, company: slug (title-cased), location, source: "greenhouse_api"}` to results

On HTTP error (4xx/5xx): log `[GREENHOUSE FAIL] {slug} — {status}` and continue to next slug.

---

### Level 2 — Playwright Crawl

For each domain in `job_boards`, for each keyword in `target_keywords`:

1. Construct a search URL appropriate for the board (e.g. `https://boards.greenhouse.io/jobs?q={keyword}`).
2. Navigate with Playwright (networkidle wait, standard config — no stealth required for public boards).
3. Extract all job listing elements. For each listing:
   - Capture title text and href link (`/jobs/`, `/roles/`, `/positions/` patterns).
   - Reconstruct absolute URL if href is relative.
4. Apply title filter (same as Level 1).
5. Add passing results to list with `source: "playwright"`.

Do not click into individual job pages at this stage — URL + title is sufficient for the orchestrator.

---

### Level 3 — Web Search (fallback)

Run up to **5 search queries** using the WebSearch tool. Query pattern:
```
site:{board_domain} "{keyword}" "{location}"
```

Use combinations of:
- `board_domain`: entries from `job_boards`
- `keyword`: entries from `target_keywords`
- `location`: entries from `location_whitelist`

For each search result URL that matches a job board domain:
- Extract title from the result snippet or URL slug
- Apply title filter
- Add to list with `source: "web_search"`

---

### Deduplication

After all three levels complete, deduplicate by URL. Keep the first occurrence (Level 1 results take priority over Level 2, Level 2 over Level 3, since earlier levels are more reliable).

---

### Cap

Apply `listing_limit` cap to the final deduplicated list. If results exceed the cap, prefer Level 1 results, then Level 2, then Level 3.

---

### Return

Return the filtered, deduplicated, capped list to the scout orchestrator. Do not write to any file directly.

---

## Failure Handling

- Greenhouse API failures: skip slug, continue
- Playwright navigation failure: log `[CRAWL FAIL] {domain}` and skip that domain
- Web search failure: log `[SEARCH FAIL]` and skip remaining Level 3 queries
- If all three levels return zero results: return `[]` — not an error
