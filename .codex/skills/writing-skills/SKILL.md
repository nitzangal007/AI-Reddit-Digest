---
name: writing-skills
description: Use when creating a new skill, editing an existing skill, or improving skill triggers and structure for this project.
---

# Writing Skills

## Overview

Use this skill to create or improve project skills.

The goal is not to write a long document.
The goal is to create a skill that is:
- discoverable
- focused
- reusable
- easy for Codex to trigger correctly

## When to Use

Use this skill when:
- adding a new project skill
- merging or splitting skills
- rewriting a weak description
- improving skill structure
- adapting external skill ideas to this repo

## Rules for Good Skills

A good skill should have:
1. one clear purpose
2. one clear trigger pattern
3. a short, direct description
4. a practical workflow
5. a clear output format
6. minimal overlap with other skills

A bad skill is:
- vague
- too broad
- too ceremonial
- mostly philosophy with no usable workflow
- overlapping heavily with another skill

## Required Workflow

### Step 1 - Define the Problem

State:
- what recurring problem this skill solves
- when Codex should use it
- when Codex should NOT use it

### Step 2 - Choose the Scope

Decide whether the skill is:
- debugging
- planning
- verification or review
- meta or process
- project-specific operations

Keep the scope narrow.

### Step 3 - Write Strong Frontmatter

Use:
- `name` with letters, numbers, and hyphens only
- `description` starting with "Use when..."

Description should say when to use the skill, not summarize the whole workflow.

### Step 4 - Write the Smallest Useful Skill

Prefer this structure:
- Overview
- When to Use
- Required Workflow
- Required Output Format
- Red Flags

Keep it concise.
Do not add huge essays.

### Step 5 - Smoke Test the Skill

Test the skill with one explicit prompt in Codex.
Example:
"Use the [skill-name] skill for this task."

Then check:
- did Codex understand when to apply it
- did it follow the workflow
- was anything unclear or too vague

### Step 6 - Refine

If the skill was ignored or used badly:
- tighten the description
- reduce overlap
- simplify the workflow
- sharpen the trigger conditions

## Naming Guidelines

Good names:
- `systematic-debugging`
- `design-and-planning`
- `review-and-verification`

Avoid:
- vague names
- internal jokes
- names with spaces or punctuation
- names that overlap too much with another skill

## Required Output Format

When asked to create or edit a skill, return:
1. Proposed folder name
2. Proposed `name`
3. Proposed `description`
4. Why this skill should exist
5. Full `SKILL.md`
6. One smoke-test prompt

## Red Flags

Stop and rethink if:
- the skill duplicates another skill
- the description explains "how" instead of "when"
- the skill has multiple unrelated jobs
- the workflow is too big for a single skill
- the skill is so vague that Codex would not know when to trigger it