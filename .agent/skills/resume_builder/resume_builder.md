---
description: Selects career data and executes the docx remodeler, bridging the user's knowledge base with the global master resume template.
globs:
  - ".users/*/*"
  - "directives/*"
  - "execution/*"
---

# Resume Builder Skill (Phase 3 Engine)

## Multi-Tenant Guardrails
- **CRITICAL**: You must only look for data within the specific user's directory (`.users/{user_id}/`).
- The final output file MUST be saved in the exact specific user's directory (`.users/{user_id}/`).
- Never leak data from or save data to other users' directories.



## Selection Logic
1. **Source**: Read the user's knowledge base at `.users/{user_id}/knowledge.md`.
2. **Relevance Scoring**: Rank every Experience and Project in `knowledge.md` against the JD.
3. **Selective Slotting**:
    - **Primary Slots (1 & 2)**: These MUST be filled with the highest-scoring matches (0.8+ score).
    - **Optional Slot (3)**: Only fill the 3rd Experience or Project slot if the relevance score is high (0.6+) AND the total content is concise enough to fit on one page. Always proioritize more recent expiriences, and always prioritize university expirience
4. **Space Management**:
    - If a 0.9 match is extremely detailed, prefer only 2 high-impact projects over 3 mediocre ones. 
    - If you include a 3rd item and the resume feels crowded, your priority is to **drop the lowest-scoring project** entirely by assigning its slots to `""`.
4. **Bullet Point Density**: If an experience is highly relevant but too long, shorten the bullet points to their most quantifiable metrics to save vertical lines.
3. **Space Optimization**: If the user has fewer than 3 items, provide empty strings `""` for the remaining slots to allow the script to collapse those sections.

## Mandatory Step: Dynamic Slot Extraction
Before generating `resume_args.json`, you **MUST** extract the actual placeholders from the template:
1. **Tool Call**: Run a Python one-liner to list all strings matching `[SLOT_...]` inside `directives/global_master.docx`. 
2. **Verification**: Map your selected content **ONLY** to these extracted keys. 
3. **Rename & Sync**: If your internal variable name differs from the document's slot name, you must use the document's name as the JSON key.
4. **Null Fill**: Include every extracted slot in your JSON. If you have no data for a slot, assign it `""`.

## Formatting & Injection Rules
- **Bullet Points**: Provide **Raw Text Only**. Strip all leading dashes (`-`) or asterisks (`*`). 
- **Zero-Colon Skill Policy**: When providing data for [SLOT_Skill_Set_X], provide the raw category name ONLY (e.g., 'Languages'). Do not include any colons or trailing punctuation, as the template already contains the colon.
- **Action Verbs**: Every bullet point must begin with a strong, job-aligned Action Verb.
- **Date Snap**: Prefix all `[SLOT_Dates_...]` values with a single Tab character (`\t`) for right-alignment. Also, make sure to store dates exactly how they are written in the knowledge base.

## Clean Execution Protocol
You are forbidden from using `python -c` wrappers for the final execution.

**Step 1:** Create the directory `.tmp/{user_id}/` if it does not exist.
**Step 2:** Save the mapping JSON to `.tmp/{user_id}/resume_args.json`.
**Step 3:** Call the script directly:
```bash
python ./execution/remodel_docx.py "./.users/{user_id}/{user_id}_{job_title}_{company}resume.docx" "./.tmp/{user_id}/resume_args.json"