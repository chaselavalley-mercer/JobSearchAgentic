---
description: Analyze a user's knowledge.md against a specific JD to find gaps and refactor content.
globs: ["users/**/knowledge.md", "jds/*.md"]
---

# Career Architect (Alignment Engine)

## Goal
Perform a deep gap analysis and generate the "Refactored Content" needed to fill the slots in the resume template.

## Instructions
1. **Cross-Reference**: Compare `knowledge.md` from the user's folder against the target JD.
2. **Match Scoring**:
    - **Technical Fit %**: Based on actual skills in `knowledge.md`.
    - **ATS Score %**: Based on current phrasing.
3. **The Delta**: List missing keywords and required "Bridge Skills."
4. **Refactor Output**: 
    - Generate a list of "Injectable Bullets" tailored to the JD.
    - **Formatting**: Output these as a JSON or a specific Markdown block that the **Resume Engine** can easily parse.
    These injectable bullets should account for all sections on the Resume Template.

## Constraints
- **Data Integrity**: Only use experiences found in the user's specific `knowledge.md`.
- **2026 Ready**: Use high-impact verbs and modern technical terminology.