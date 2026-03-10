---
description: 'Strict execution protocol for dispatching job nodes to Slack/Discord via MCP tools. Activate ONLY when Phase 2 Resume Match Score and Gaps are verified'
---

# Job Dispatcher Skill (DOE Framework)

## Layer 1: Directive
- **CRITICAL CONSTRAINT**: You MUST NOT summarize, estimate, or change the match score under any circumstances.
- You must extract the **exact score** and the **top 3 gaps** directly from `.tmp/phase2_analysis.json`.
- Preserve the integrity of the data; pass it exactly as it exists in the JSON file.

## Layer 2: Orchestration
- **Step 1**: FIRST, use the `slack_list_channels` tool (via MCP) to dynamically find the ID for the `#job-leads` channel. Do not guess or hardcode the channel ID.
- **Step 2**: THEN, format the payload using the extracted exact score and gaps.
- **Step 3**: Call the `slack_post_message` tool (via MCP) to dispatch the job node to the identified channel.

## Layer 3: Execution
- **Self-Annealing Protocol**: If the MCP tool fails at any stage (e.g., channel not found, API error), you are **FORBIDDEN** from trying to write a custom Python script, `curl` command, or wrapper to bypass it. 
- You must immediately STOP, read the exact tool error, display it, and ask the user for explicit permission to re-try or troubleshoot the MCP connection.

## Mandatory Guardrail
- **Proof of Dispatch**: You must produce a **Walkthrough Artifact** as proof of dispatch before ending the task. The task is not considered complete until this artifact is generated and provided to the user detailing the successful payload transmission.
