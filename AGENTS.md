# AGENTS.md

Before making code changes, read this file first.

Then check the available skills under `.codex/skills/` and use the most relevant one.

## Available Skills

- `systematic-debugging`
  Use for bugs, failed behavior, wrong digest content, wrong subreddit routing, broken Telegram flow, scheduler issues, email issues, and unexpected runtime behavior.

- `design-and-planning`
  Use for new features, behavior changes, non-trivial refactors, deployment planning, onboarding changes, settings changes, digest flow changes, and architecture decisions.

- `review-and-verification`
  Use before claiming work is complete, before commit, before PR, or when verifying whether a fix or feature is actually done.

- `writing-skills`
  Use when creating a new skill, editing an existing skill, merging skills, splitting skills, or improving skill triggers and descriptions.

- `documentation-and-reporting`
  Use when creating, moving, naming, or classifying docs under `docs/`, writing planning reports, architecture notes, ADRs, incident notes, progress reports, or maintaining `docs/README.md`.

## Project Priorities

- Prefer minimal diffs.
- Preserve existing behavior unless the task explicitly requires behavior change.
- Do not perform unrelated refactoring.
- Do not jump into implementation before understanding the task.
- For medium and large tasks, design and planning come before code.
- Do not claim a task is complete without fresh verification evidence.

## Retrieval Debug Order

For retrieval, routing, digest quality, or subreddit selection issues, inspect in this order:

1. `app/nlu.py`
2. `app/registry.py`
3. `app/conversation.py`
4. `app/reddit_client.py`
5. `app/ai_engine.py`

When debugging retrieval issues, do not propose prompt-only fixes before checking routing and fetch behavior.

## Bot and Runtime Debug Order

For Telegram, scheduler, persistence, email, or runtime issues, inspect in this order:

1. `app/telegram_bot.py`
2. `app/user_store.py`
3. `app/scheduler.py`
4. `app/email_notifier.py`

## Working Style

Before implementation, usually return:

1. Task understanding
2. Likely affected files
3. Recommended approach
4. Implementation plan
5. Verification plan
6. Risks or regression concerns

For small isolated edits, keep this brief.
For medium and large tasks, make it explicit.

## Documentation Policy

- `docs/` root is reserved for the main navigation index and other rare repo-wide entry points only.
- Do not place plans, reports, architecture notes, incident notes, or feature docs directly in `docs/` root.
- Every new markdown document must go in the most appropriate topic folder under `docs/`.
- Preferred top-level folders are:
  - `docs/architecture/`
  - `docs/planning/`
  - `docs/decisions/`
  - `docs/operations/`
  - `docs/reports/`
  - `docs/features/`
- When a topic will have multiple related documents, create or reuse a topic subfolder instead of dropping files loosely into the parent folder.
- Use professional, stable names. Prefer dated names like `YYYY-MM-DD-<topic>.md` for plans, reports, and incident notes.
- When adding, moving, or renaming meaningful documentation, update `docs/README.md` so the docs remain navigable.
- Avoid duplicate documentation. If a document already exists for the topic, update or supersede it deliberately instead of creating a near-copy.
- Planning, architecture, operations, and decision changes should normally update documentation in the same task unless the user explicitly asks not to.

## Verification Standard

Do not say:
- "done"
- "fixed"
- "works"
- "passes"

unless fresh verification was performed and the evidence supports the claim.

If something is only partially verified, say so clearly.

## Project-Specific Notes

- Wrong digest content is often a pipeline issue, not only a prompting issue.
- Explicit subreddit digests must be checked against override behavior.
- Scheduler issues must be traced through both stored user preferences and scheduled execution.
- Email issues must be checked at both configuration level and actual send execution level.
- Deployment work must separate code changes from infrastructure decisions.

## Default Prompting Behavior

If the task is a bug:
- use `systematic-debugging`

If the task is a feature, refactor, or deployment change:
- use `design-and-planning`

If the task appears complete and needs validation:
- use `review-and-verification`

If the task is about building or editing skills:
- use `writing-skills`

If the task is about docs structure, reports, plans, ADRs, or navigation under `docs/`:
- use `documentation-and-reporting`
