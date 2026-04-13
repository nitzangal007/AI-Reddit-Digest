---
name: review-and-verification
description: Use when a task, fix, or feature seems complete and you need review plus fresh verification evidence before claiming success.
---

# Review and Verification

## Overview

Use this skill before claiming work is done.

Core rule:

NO "DONE", "FIXED", OR "PASSING" CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.

Review first.
Verify second.
Claim success last.

## When to Use

Use this skill when:
- a bugfix looks complete
- a feature implementation looks complete
- you are about to commit
- you are about to open a PR
- you want to know what is still unverified
- you want a strict quality gate before moving on

## Required Workflow

### Step 1 - Restate the Claim

State exactly what is being claimed, for example:
- digest routing is fixed
- onboarding flow works
- daily digest scheduling works
- email delivery works
- deployment is healthy

### Step 2 - Review Against Intent

Check whether the implementation matches:
- the user request
- the approved design
- the implementation plan

List missing items or uncertainty explicitly.

### Step 3 - Run Fresh Verification

Identify the commands or checks that prove the claim.

Examples:
- `pytest ...`
- targeted script or manual flow
- Telegram command flow validation
- scheduler or log validation
- email send test
- deployment health or log check

Do not rely on earlier runs.
Do not rely on assumption.
Do not rely on "it should work now."

### Step 4 - Read Actual Results

For each verification:
- note command or check run
- note success or failure
- note what remains unverified

### Step 5 - Return Honest Status

Return one of:
- Verified complete
- Partially verified
- Not verified
- Failing, with evidence

## Project-Specific Verification Checklist

For retrieval changes:
- test one broad topic query
- test one entity-specific query
- test one previous failure case
- confirm no obvious regression in unrelated routing

For Telegram changes:
- test the exact command or callback flow changed
- confirm user state or preferences still persist correctly

For scheduler or email changes:
- verify trigger conditions
- verify execution path
- verify visible output or logs
- verify failure path if relevant

For deployment changes:
- verify startup
- verify required environment variables
- verify logs or health
- verify scheduled behavior assumptions

## Required Output Format

Always return:
1. Claimed outcome
2. Review findings
3. Verification steps run
4. Actual results
5. Remaining gaps
6. Final status

## Red Flags

Stop and do not claim success if:
- no fresh verification was run
- only part of the requirement was checked
- only linting passed but runtime behavior was not checked
- the agent reported success but no independent evidence was reviewed
- important requirements remain unverified