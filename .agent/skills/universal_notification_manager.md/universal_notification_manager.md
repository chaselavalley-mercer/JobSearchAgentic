---
name: universal-notification-scout
description: Activates when the user needs to monitor, extract, or process job alerts from major platforms (LinkedIn, Indeed, Glassdoor, Handshake) via email or notification summaries.
---

# Universal Notification Scout Skill
[cite_start]**Goal**: To autonomously identify and extract job opportunities from high-protection platforms without triggering anti-bot measures by using email/notification surfaces as the primary data source[cite: 85, 113].

## Instructions
1. [cite_start]**Source Selection**: Use the Browser Subagent to navigate to the user's primary email provider (e.g., Gmail, Outlook)[cite: 103, 118].
2. **Alert Identification**:
   - Search for specific sender patterns: `jobs-listings@linkedin.com`, `alert@indeed.com`, `no-reply@glassdoor.com`.
   - [cite_start]Filter for alerts received within the last "User-Defined" window (default: 24 hours)[cite: 181].
3. **Deep Extraction**:
   - Open each relevant alert email.
   - [cite_start]Use the Browser Subagent to "read" the email body and extract the **Job Title**, **Company**, and **Direct Application URL**[cite: 115, 117].
   - [cite_start]**Crucial**: If the email only contains a "View Job" button, click it to navigate to the job page, then immediately extract the full Job Description (JD) text as a Markdown Artifact[cite: 34, 189].
4. **Data Normalization**:
   - [cite_start]Save the results into `.tmp/raw_leads/` using a standardized naming convention: `COMPANY_ROLE_DATE.md`[cite: 186, 225].
5. [cite_start]**Orchestration Handoff**: Once 5+ leads are extracted, signal the "Analyst Agent" to begin RAG-based resume tailoring[cite: 89, 111].

## Constraints
- [cite_start]**Anti-Bot Compliance**: Never perform more than 10 rapid-fire navigation actions on a single job board domain; pause for 60 seconds between batches to mimic human reading speed[cite: 33, 116].
- [cite_start]**No Direct Search**: Do not use the search bars on LinkedIn or Indeed; only process jobs provided via the notification links[cite: 57].
- [cite_start]**Privacy**: Never extract or log personal login credentials into the workspace files[cite: 151, 164].

## Examples
- **Input**: "Check my LinkedIn alerts for AI Engineer roles from today."
- [cite_start]**Output**: 5 Markdown files in `.tmp/raw_leads/` and a summary Artifact in the Agent Manager[cite: 128, 132].