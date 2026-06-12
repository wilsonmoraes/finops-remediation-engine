---
name: api-test
description: Run the canonical test suite for the FinOps Remediation Engine. Use when the user asks to run tests, check the suite, or verify the backend after a change.
allowed-tools: Bash
argument-hint: [pytest args, optional]
---

# /api-test — Canonical Test Suite

!`python -m pytest -q $ARGUMENTS`

Report only:
- Pass/fail counts
- Failures with `file:line` and a one-line reason

Do not paste the full pytest output unless there are failures.
