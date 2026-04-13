---
name: systematic-debugging
description: Use when a bug, failed digest, wrong subreddit routing, broken Telegram flow, scheduler issue, email issue, or unexpected behavior appears, before proposing fixes.
---

# Systematic Debugging

## Overview

Use this skill for bugs and unexpected behavior in the Reddit Digest project.

Core rule:

NO FIXES BEFORE ROOT CAUSE ANALYSIS.

Do not guess.
Do not stack random fixes.
Do not say "probably" and patch blindly.

## When to Use

Use this skill when:
- a digest talks about the wrong topic
- explicit subreddit requests return unrelated content
- NLU confidence or entity routing looks wrong
- Telegram commands or onboarding behave incorrectly
- daily or weekly digest delivery does not run as expected
- email delivery fails
- tests fail
- behavior changed after a recent edit

Do not skip this skill just because the issue looks small.

## Project Debug Order

For retrieval and content issues, inspect in this order:
1. `app/nlu.py`
2. `app/registry.py`
3. `app/conversation.py`
4. `app/reddit_client.py`
5. `app/ai_engine.py`

For bot and runtime issues, inspect in this order:
1. `app/telegram_bot.py`
2. `app/user_store.py`
3. `app/scheduler.py`
4. `app/email_notifier.py`

## Required Workflow

### Phase 1 - Reproduce and Locate

1. Restate the bug in one sentence.
2. Describe exact reproduction steps.
3. Identify whether the issue is mainly:
   - retrieval
   - summarization or prompting
   - Telegram UX
   - scheduling
   - email delivery
   - deployment or runtime
4. Collect direct evidence before suggesting any fix.

### Phase 2 - Trace the Pipeline

If this is a retrieval bug, trace:
- user query
- parsed topic
- detected entities
- selected subreddits
- fallback path
- fetched posts
- final response behavior

If this is a bot or runtime bug, trace:
- command or trigger
- handler
- persistence or state
- scheduled execution
- external dependency
- output or logs

### Phase 3 - Form One Hypothesis

State exactly:

"I think the root cause is X because Y."

Test only one hypothesis at a time.

### Phase 4 - Fix Minimally

After the root cause is identified:
1. make the smallest relevant change
2. avoid unrelated refactoring
3. preserve existing behavior outside the bug
4. define what must be verified after the fix

## Required Output Format

Always return:
1. Bug summary
2. Suspected layer
3. Evidence collected
4. Root cause hypothesis
5. Minimal fix plan
6. Verification plan
7. Regression risk

## Red Flags

Stop and restart analysis if you are about to:
- propose a fix before showing evidence
- change multiple files "just in case"
- use words like "probably" or "maybe" as the main basis
- skip logs, traces, or actual outputs
- claim the issue is solved before verification

## Project-Specific Reminders

- Wrong digest content is often a pipeline problem, not a prompt-only problem.
- Explicit subreddit digests must be checked against subreddit override behavior.
- Scheduler issues must be traced through both user preferences and the scheduled job path.
- Email issues must be checked at both configuration and send execution levels.