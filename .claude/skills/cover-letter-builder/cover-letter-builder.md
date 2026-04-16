---

## 2. New Cover Letter Builder (`cover_letter_builder.md`)

This skill uses the **`cover-letter-template.html`** created earlier and focuses on the "Pain Point" analysis found in your database.

```markdown
---
description: Generates a tailored cover letter PDF based on JD pain points and your professional STAR stories.
globs:
  - ".users/*/*"
  - "templates/cover-letter-template.html"
  - "execution/generate-pdf.mjs"
---

# Cover Letter Builder Skill

## Data Sourcing
1. **Job Intel**: Fetch the `company_description` and `requirements` from the `scraped_json` in `jobs.db`.
2. **Gap Analysis**: Use the `evaluation_json` to identify which specific "Superpowers" or STAR stories from your `knowledge.md` mitigate the company's risks.

## Narrative Construction
1. **The Hook**: Open with a `company_specific_hook` (e.g., referencing their recent AI initiatives or specific tech stack).
2. **The Proof**: Select one high-impact STAR story (e.g., your Autonomous Job Search Engine or StemForge project) that matches the role's primary challenge.
3. **The Bridge**: End with your "Exit Narrative"—why you are graduating from Mercer and choosing *this* specific company for your next engineering chapter.

## Mandatory Template Mapping
Map to `templates/cover-letter-template.html`:
- `{{DATE}}`: Current system date.
- `{{COMPANY_NAME}}`, `{{RECIPIENT_NAME}}`: From database.
- `{{LETTER_BODY}}`: The 3-paragraph tailored narrative.

## Execution Protocol
**Step 1:** Create `.tmp/{user_id}/letter_tailored.html` by injecting values into the template.
**Step 2:** Execute the PDF generator:
```bash
node ./execution/generate-pdf.mjs "./.tmp/{user_id}/letter_tailored.html" "./.users/{user_id}/Chase_LaValley_{Company}_Cover_Letter.pdf" --format=letter