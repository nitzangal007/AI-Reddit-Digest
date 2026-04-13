---
name: documentation-and-reporting
description: Use when creating, classifying, moving, or updating documentation under docs/, including plans, architecture notes, ADRs, incident notes, progress reports, and docs navigation.
---

# Documentation And Reporting

## Overview

Use this skill when the task is about documentation structure or durable project records.

The goal is to keep `docs/` clean, predictable, and easy to navigate.

This skill is for:

- deciding where a new document belongs
- naming documents consistently
- updating `docs/README.md`
- avoiding duplicate or misplaced docs
- ensuring meaningful planning, architecture, operations, or decision changes are reflected in documentation

## When To Use

Use this skill when:

- adding a plan, rollout doc, or roadmap note
- writing an architecture note or system-boundary document
- recording a decision or ADR
- writing an incident note, runbook, or operational follow-up
- adding a progress report, retrospective, or post-project summary
- creating or reorganizing feature-specific docs
- cleaning up docs structure or naming

Do not use this skill for:

- code comments
- tiny README wording fixes with no structural implications
- one-off markdown scratch notes that should not live in the repo

## Folder Classification Rules

Place documents by purpose first:

- `docs/architecture/`
  Use for system boundaries, data flow, component structure, and technical design references.

- `docs/planning/`
  Use for proposed work, rollout phases, implementation plans, migration plans, and project plans.

- `docs/decisions/`
  Use for ADR-style records or short decision notes when alternatives and rationale matter.

- `docs/operations/`
  Use for incident notes, operational runbooks, recovery notes, and deployment-operation references.

- `docs/reports/`
  Use for progress reports, retrospectives, status summaries, and outcome writeups.

- `docs/features/`
  Use for feature-specific docs that are not primarily plans, architecture notes, decisions, or operations material.

When a document belongs to an ongoing topic, create or reuse a stable topic subfolder such as:

- `docs/planning/deployment/`
- `docs/features/telegram/`
- `docs/architecture/retrieval/`

Do not place these documents directly in `docs/` root.

## Naming Rules

- Prefer concise, professional file names.
- Prefer dated names like `YYYY-MM-DD-<topic>.md` for plans, reports, and incidents.
- Prefer stable evergreen names only for long-lived reference docs.
- Avoid vague names like `notes.md`, `plan.md`, or `update.md`.

## Required Workflow

### Step 1 - Inspect Existing Docs

Before adding a new doc:

1. inspect `docs/`
2. inspect `docs/README.md` if it exists
3. check whether a document for the same topic already exists

### Step 2 - Classify The Document

Decide whether it is:

- a plan
- an architecture document
- a decision record
- an incident or operations note
- a progress report or retrospective
- a feature document

If the document seems to fit multiple categories, choose the primary purpose and note cross-links inside the file if needed.

### Step 3 - Choose The Folder

Put the file in the most specific stable folder that matches its purpose.

Rules:

- prefer an existing topic subfolder when one already fits
- create a new topic subfolder only when it will remain useful and intuitive
- do not create deep hierarchies without a clear reason

### Step 4 - Avoid Duplicates

Before creating a new file, check whether you should:

- update an existing document
- replace an outdated document with a clearer successor
- add a new document that references the older one intentionally

Do not create near-duplicate files for the same topic and same purpose.

### Step 5 - Update Navigation

Update `docs/README.md` when:

- a meaningful new document is added
- a new topic folder becomes part of normal navigation
- documents are moved or renamed
- the docs structure changes

### Step 6 - Keep Docs In Sync

If a task materially changes:

- planning
- architecture
- operations
- delivery workflow
- decision rationale

then documentation should usually be updated in the same task unless the user explicitly says not to.

## Required Output Format

Return:

1. Document classification
2. Chosen folder and file name
3. Why that location fits best
4. Whether `docs/README.md` was updated
5. Any duplicate or superseded docs found

## Red Flags

Stop and rethink if:

- the file would land directly in `docs/` root even though it is not the main index
- the same topic already has multiple overlapping docs
- the folder name is vague or temporary
- the hierarchy is getting deeper without better discoverability
- the docs change is meaningful but `docs/README.md` was left stale
