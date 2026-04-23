---
name: html-resume-builder
description: >
  Produces a tailored HTML resume and cover letter by injecting content into
  cv-template.html and cover-letter-template.html. Called by /generate_docs
  after career-architect has run. Outputs two HTML files to .tmp/chase_lavalley/.
  Does NOT call docx_assembler.py or any Python script.
---

# HTML Resume Builder Skill

**Layer**: 2 (Orchestration)
**Called by**: `.claude/commands/generate_docs.md` — Phase 3a
**Inputs**:
  - `.tmp/chase_lavalley/career_analysis.json` — ranked slot mapping from career-architect
  - `.tmp/chase_lavalley/current_job.json` — job data (title, company, location, etc.)
  - `.users/chase_lavalley/knowledge.md` — master skill + experience inventory
  - `templates/cv-template.html` — resume template
  - `templates/cover-letter-template.html` — cover letter template
**Outputs**:
  - `.tmp/chase_lavalley/resume_tailored.html`
  - `.tmp/chase_lavalley/letter_tailored.html`

---

## Step 1 — Read All Inputs

Read these four files before generating any content:
1. `.tmp/chase_lavalley/career_analysis.json`
2. `.tmp/chase_lavalley/current_job.json`
3. `.users/chase_lavalley/knowledge.md`
4. `templates/cv-template.html`
5. `templates/cover-letter-template.html`

Do not begin writing output until all five are read.

---

## Step 2 — Build the Resume HTML

Take the full text of `templates/cv-template.html` and replace every
`{{PLACEHOLDER}}` with the values below.

### Static fields (always the same)

| Placeholder | Value |
|---|---|
| `{{LANG}}` | `en` |
| `{{NAME}}` | `Chase LaValley` |
| `{{PAGE_WIDTH}}` | `8.5in` |
| `{{PHONE}}` | `404-563-9242` |
| `{{EMAIL}}` | `11037074@live.mercer.edu` |
| `{{LINKEDIN_URL}}` | `https://linkedin.com/in/chase-lavalley-cemu` |
| `{{LINKEDIN_DISPLAY}}` | `linkedin.com/in/chase-lavalley-cemu` |
| `{{PORTFOLIO_URL}}` | *(empty string)* |
| `{{PORTFOLIO_DISPLAY}}` | *(empty string)* |
| `{{LOCATION}}` | `Smyrna, GA` |
| `{{SECTION_SUMMARY}}` | `Professional Summary` |
| `{{SECTION_COMPETENCIES}}` | `Core Competencies` |
| `{{SECTION_EXPERIENCE}}` | `Work Experience` |
| `{{SECTION_PROJECTS}}` | `Project Highlights` |
| `{{SECTION_EDUCATION}}` | `Education` |
| `{{SECTION_CERTIFICATIONS}}` | `Certifications` |
| `{{SECTION_SKILLS}}` | `Technical Skills` |

### `{{SUMMARY_TEXT}}`

Write a 2–3 sentence tailored professional summary. It must:
- Open with a role-specific identity statement (e.g. "AI Engineering student...")
- Reference 2–3 specific skills from `knowledge.md` that match the JD
- Close with a forward-looking sentence about impact or contribution
- Never mention the company name directly
- Never exceed 60 words

### `{{COMPETENCIES}}`

Extract 10–15 keywords from the job description that match skills in
`knowledge.md`. Render each as:

```html
<span class="competency-tag">Keyword</span>
```

Prioritize exact-match technical terms over generic nouns. No duplicates.

### `{{EXPERIENCE}}`

Include all three work experiences from `knowledge.md` in reverse
chronological order. For each:

```html
<div class="job">
  <div class="job-header">
    <span class="job-company">Company | Location</span>
    <span class="job-period">Date Range</span>
  </div>
  <div class="job-role">Job Title</div>
  <ul>
    <li>Bullet point one</li>
    <li>Bullet point two</li>
    <li>Bullet point three</li>
  </ul>
</div>
```

Rules:
- Use the exact bullets from `knowledge.md` as the source of truth
- Reorder bullets within a job to lead with the most JD-relevant one
- Never duplicate a bullet across two different jobs
- Never invent metrics, tools, or outcomes not in `knowledge.md`
- Strong action verb at the start of every bullet

### `{{PROJECTS}}`

Include the top 2 most JD-relevant projects from `knowledge.md`.

Project selection logic:
- For AI/automation/agentic roles: lead with **AI Career Architect & Auto-Applier**, second is the most relevant remaining project
- For embedded/hardware/CV roles: lead with **AI Smart Fan**, second is the most relevant remaining project

For each project:

```html
<div class="project">
  <div class="project-title">Project Name
    <span class="project-badge">Tech · Stack · Here</span>
  </div>
  <div class="project-desc">Bullet one from knowledge.md</div>
  <div class="project-desc">Bullet two from knowledge.md</div>
  <div class="project-desc">Bullet three from knowledge.md</div>
</div>
```

Never invent bullets. Use the exact text from `knowledge.md`, optionally
trimmed for length.

### `{{EDUCATION}}`

```html
<div class="edu-item">
  <div class="edu-header">
    <span class="edu-title">B.S.E. —
      <span class="edu-org">Mercer University</span>
    </span>
    <span class="edu-year">May 2026</span>
  </div>
  <div class="edu-desc">Computer Engineering Specialization · GPA: 3.3/4.0</div>
</div>
```

### `{{CERTIFICATIONS}}`

Leave empty — render nothing between the section tags for now.

### `{{SKILLS}}`

Build one `<span class="skill-item">` per skill category in `knowledge.md`:

```html
<div class="skills-grid">
  <span class="skill-item">
    <span class="skill-category">Languages:</span> Python, SQL, TypeScript, C++, Java
  </span>
  <span class="skill-item">
    <span class="skill-category">AI & Automation:</span> Claude Code, Agentic Workflows, n8n, MCP, LLM API Orchestration, OpenAI API, GoHighLevel
  </span>
  <span class="skill-item">
    <span class="skill-category">Tools & Infrastructure:</span> Git/GitHub, Docker, Linux, Raspberry Pi, OpenCV, VS Code
  </span>
</div>
```

Derive the values from `knowledge.md` — do not hardcode if the file has changed.

---

## Step 3 — Build the Cover Letter HTML

Take the full text of `templates/cover-letter-template.html` and replace
every `{{PLACEHOLDER}}` as follows:

| Placeholder | Value |
|---|---|
| `{{LANG}}` | `en` |
| `{{NAME}}` | `Chase LaValley` |
| `{{PHONE}}` | `404-563-9242` |
| `{{EMAIL}}` | `11037074@live.mercer.edu` |
| `{{LOCATION}}` | `Smyrna, GA` |
| `{{DATE}}` | Today's date formatted as e.g. `April 19, 2026` |
| `{{RECIPIENT_NAME}}` | `Hiring Manager` |
| `{{RECIPIENT_TITLE}}` | *(empty string)* |
| `{{COMPANY_NAME}}` | Company name from `current_job.json` |

### `{{LETTER_BODY}}`

Three `<p>` tags, no more:

**Paragraph 1 — Hook**
- Open with a specific, genuine observation about the company or role
- Name the exact role title from the JD
- 2–3 sentences max

**Paragraph 2 — Proof**
- One STAR story (Situation/Task, Action, Result) from `knowledge.md`
- Choose the experience most relevant to the JD's core requirements
- Quantify the result if a metric exists in `knowledge.md`
- 3–4 sentences max

**Paragraph 3 — Bridge**
- State specifically why this role/company aligns with Chase's direction
- Reference something concrete from the JD (team focus, tech stack, mission)
- Close with a direct expression of interest in next steps
- 2–3 sentences max

Example structure:
```html
<p>Paragraph one text here.</p>
<p>Paragraph two text here.</p>
<p>Paragraph three text here.</p>
```

---

## Step 4 — Write Output Files

Write the completed resume HTML to:
  `.tmp/chase_lavalley/resume_tailored.html`

Write the completed cover letter HTML to:
  `.tmp/chase_lavalley/letter_tailored.html`

Then print:
```
[HTML RESUME] Written to .tmp/chase_lavalley/resume_tailored.html
[HTML LETTER] Written to .tmp/chase_lavalley/letter_tailored.html
```

---

## Constraints

- **Never fabricate** metrics, tools, companies, or outcomes not in `knowledge.md`
- **Never modify the CSS** in the templates — only replace `{{PLACEHOLDER}}` tokens
- **Never leave a `{{PLACEHOLDER}}`** in the output — every token must be replaced
- **Never call** `docx_assembler.py`, `resume_builder.md`, or any Python script
- The HTML files must be self-contained and renderable in a browser
