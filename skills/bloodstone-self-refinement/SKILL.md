---
name: bloodstone-self-refinement
description: Capture repo-specific lessons from a just-completed task into AGENTS.md or local skills. Use when the user asks to save what was learned, self-refine the workflow, update instructions after a mistake or discovery, add durable notes to an existing skill, or create a new skill from a repeated workflow.
---

# Bloodstone Self Refinement

Use this skill after a real task exposed a reusable lesson. Keep the saved guidance short, procedural, and local to this repo.

## Choose The Destination

1. Put the lesson in `AGENTS.md` when it is a repo-wide default, preference, trigger rule, or external reference path that should shape future turns broadly.

2. Put the lesson in an existing skill when it changes how a known workflow should be executed.
- Add pitfalls, decision points, verification commands, or external references that repeatedly matter for that workflow.
- Prefer updating an existing skill over creating a near-duplicate skill.

3. Create a new skill only when the workflow is distinct, recurring, and worth triggering on its own.
- Good candidates: multi-step procedures, fragile sequences, or repo-specific operating patterns that will recur across turns.
- If the lesson is only one or two bullets inside an existing workflow, keep it in the existing skill instead.

## What To Save

- Save durable rules discovered from real work.
- Save short workflow corrections after mistakes or dead ends.
- Save high-signal external references that repeatedly unblock the task.
- Save concrete trigger phrasing when it helps the right skill activate next time.

## What Not To Save

- Do not save one-off facts tied only to a single asset or single turn.
- Do not save long retrospectives or token-heavy narrative.
- Do not duplicate the same rule in multiple places unless the trigger surface genuinely requires it.
- Do not create a new skill if `AGENTS.md` or an existing skill can hold the lesson cleanly.

## Update Workflow

1. Summarize the lesson in one sentence before editing anything.
2. Decide whether it belongs in `AGENTS.md`, an existing skill, or a new skill.
3. Edit the minimum number of files needed.
4. If creating a new skill, initialize it properly, fill in `SKILL.md`, and register it in `AGENTS.md`.
5. Validate new skills after editing.
6. Report exactly what was saved and where.

## Validation

- For a new skill, run:
```bash
python3 /home/trard/.codex/skills/.system/skill-creator/scripts/quick_validate.py skills/<skill-name>
```
- Re-read the updated `AGENTS.md` and affected `SKILL.md` sections to make sure the wording is short and actually triggerable.
