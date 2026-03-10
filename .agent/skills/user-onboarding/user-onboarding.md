---
description: Provision a new user workspace by converting a PDF resume into a knowledge base and a template.
globs: ["users/**/*.pdf"]
---

# User Onboarding Provisioner

## Goal
Extract raw data and structural layout from a candidate's resume to create the necessary DOE infrastructure.

## Instructions
1. **Target Identification**: Locate the PDF in `users/{user_id}/`.
2. **Knowledge Extraction**: 
    - Create `users/{user_id}/knowledge.md`.
    - Extract every specific project, metric, and tech stack mentioned.
    - Format as a "Master Skill Inventory" so other agents can easily query it.
3. **Template Scaffolding**: 
    - Create `users/{user_id}/resume_template.md`.
    - Convert the PDF layout into Markdown.
    - Replace all content-heavy bullet points with unique slots (e.g., `[EXP_PROLEARN_1]`, `[PROJECT_AI_FAN]`).
    - **Note**: Keep headers, contact info, and education static.

## Constraints
- **Fidelity**: The template must mirror the PDF’s original visual hierarchy.
- **Independence**: Do not look at JDs or external files during this process.