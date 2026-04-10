---
name: design-and-planning
description: Use when adding a feature, changing behavior, planning deployment, or making a non-trivial refactor, before writing code.
---

# Design and Planning

## Overview

Use this skill before implementation when the task is larger than a tiny local edit.

Core rule:

NO CODE BEFORE A SHORT APPROVED DESIGN AND A CLEAR IMPLEMENTATION PLAN.

This skill is intentionally lighter than heavyweight enterprise planning.
Keep it practical and focused.

## When to Use

Use this skill when:
- adding a new feature
- changing user-facing behavior
- redesigning retrieval flow
- planning always-on deployment
- changing onboarding, settings, digests, scheduling, or email behavior
- refactoring logic across multiple files

Do not use this skill for:
- typo fixes
- one-line local edits
- tiny isolated changes with no behavior impact

## Required Workflow

### Step 1 - Inspect Context

Before proposing anything:
1. inspect the relevant files
2. summarize the current behavior
3. identify likely touched files

### Step 2 - Clarify the Goal

Ask only the necessary questions.
Focus on:
- goal
- constraints
- success criteria
- what must not break

### Step 3 - Propose Options

Provide 2 or 3 approaches with trade-offs.
Recommend one approach and explain why.

### Step 4 - Present a Short Design

Present a compact design that includes:
- goal
- affected components
- data or control flow
- risks
- verification approach

Do not write code yet.
Wait for approval if the task is medium or large.

### Step 5 - Write the Plan

Create an implementation plan with:
1. ordered steps
2. exact files likely to change
3. what each step accomplishes
4. what must be verified after each major step
5. known risks or rollback notes

Prefer practical tasks, not microscopic ceremony.

## Plan Format

Use this structure:

- Goal
- Current behavior
- Proposed change
- Files likely involved
- Implementation steps
- Verification steps
- Risks or regression concerns

For larger tasks, save the plan under:
`docs/planning/<topic>/YYYY-MM-DD-<topic>.md`

Do not place planning files directly in `docs/` root.
If the repo has a docs navigation index, update it when adding a meaningful new plan.

## Project-Specific Pointers

For retrieval changes, usually inspect:
- `app/nlu.py`
- `app/registry.py`
- `app/conversation.py`
- `app/reddit_client.py`
- `app/ai_engine.py`

For bot and runtime changes, usually inspect:
- `app/telegram_bot.py`
- `app/user_store.py`
- `app/scheduler.py`
- `app/email_notifier.py`

## Red Flags

Stop and re-plan if:
- implementation started before design approval
- touched files grew beyond the original scope
- the plan includes unrelated refactoring
- the task secretly contains multiple independent subprojects
- success criteria are still vague

## Required Output Format

Return:
1. Short understanding of the goal
2. Recommended approach
3. Short design
4. Implementation plan
5. Verification plan
6. Risks
