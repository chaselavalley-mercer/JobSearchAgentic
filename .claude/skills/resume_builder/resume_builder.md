---
description: Tailors and builds an ATS-optimized PDF resume using database-extracted JD components and HTML templates.
globs:
  - ".users/*/*"
  - "templates/cv-template.html"
  - "execution/generate-pdf.mjs"
---

# Resume Builder Skill (HTML/PDF Engine)

## Data Sourcing
1. **Database Query**: Query `jobs.db` for the `job_id` to retrieve the `scraped_json` (raw JD) and `evaluation_json` (your gap analysis).
2. **Knowledge Base**: Read `.users/{user_id}/knowledge.md` for your master career data.

## Tailoring Logic
1. **Keyword Injection**: Extract 15-20 core keywords from the `scraped_json`.
2. **Experience Selection**: Select the top 3-4 projects or experiences based on the highest relevance scores in `evaluation_json`.
3. **Bullet Refactoring**: Rewrite selected bullets to incorporate JD-specific keywords while maintaining technical accuracy.
4. **Summary Bridge**: Create a 3-line `SUMMARY_TEXT` that connects your Mercer University Engineering background and SAE leadership to the specific needs of the company.

## Mandatory Template Mapping
Map your generated content to the following `{{PLACEHOLDERS}}` in `templates/cv-template.html`:
- `{{NAME}}`, `{{EMAIL}}`, `{{PHONE}}`, `{{LOCATION}}` (from your profile).
- `{{SUMMARY_TEXT}}`: The tailored narrative.
- `{{EXPERIENCE}}`: HTML block of tailored job entries.
- `{{COMPETENCIES}}`: A grid of JD keywords.

## Execution Protocol
**Step 1:** Create `.tmp/{user_id}/resume_tailored.html` by injecting values into the template.
**Step 2:** Execute the PDF generator:
```bash
node ./execution/generate-pdf.mjs "./.tmp/{user_id}/resume_tailored.html" "./.users/{user_id}/Chase_LaValley_{Company}_Resume.pdf" --format=letter