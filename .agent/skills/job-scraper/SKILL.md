---
name: job-scraper
description: Activates when the user wants to search for, scrape, or extract job listings, specifically including salary, location, and experience requirements.
---

# Job Scraper Skill
**Goal**: Autonomously navigate job boards to extract high-fidelity job data, including compensation and location, for "New Grad" filtering.

## Parameters
- **`user_id`** (Required): The identifier for the current user. Used to dynamically resolve settings (`.users/{{user_id}}/search_settings.md`) and outputs (`.tmp/{{user_id}}/scraped_jobs.json`).

## Instructions
1.  **Identify Target**: Use the provided URL (e.g., Greenhouse or Lever).
2.  **Initialize Browser**: Invoke the Antigravity Browser Subagent to handle dynamic content.
3.  **Data Extraction Requirements**: You MUST extract the following fields for every listing:
    * **Job Title**: The official position name.
    * **Company**: The hiring entity.
    * **Location**: City/State or "Remote" status.
    * **Pay/Salary**: Look for salary ranges, hourly rates, or "Total Rewards" sections.
    * **Experience Level**: Specifically look for keywords like "New Grad," "Entry Level," or "0-2 years".
    * **URL**: Direct link to the individual job posting.
4.  **Universal Semantic Segmenting**: For any active user, the scraper must isolate "Core Responsibilities", "Required Qualifications", and "Preferred Qualifications" into an `analysis_payload` object.
5.  **Deterministic Processing**: Pass the raw HTML or text to `scripts/scrape_jobs.py --url <URL> --user <user_id>` to ensure consistent JSON formatting.
6.  **Persistence**: Save the final structured output to `.tmp/{{user_id}}/scraped_jobs.json`.

## Constraints
* **Verification**: Always generate a **Browser Recording** artifact of the scraping session for human review.
* **Safety**: Only visit domains explicitly listed in the `browserAllowlist.txt`.
* **Focus**: If pay is not visible on the main list, click through to the job description page to find it.

## Examples
**Input**: "Scrape AI roles from Greenhouse for chase_lavalley."
**Output**: A JSON file in `.tmp/chase_lavalley/scraped_jobs.json` containing titles, companies, salary ranges, specific locations, and semantic segmentation payloads.