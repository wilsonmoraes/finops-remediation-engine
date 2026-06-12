---
name: remediation-audit
description: Audit the current diff (or a given path) for remediation-safety and determinism violations. Use when the user touches providers/detectors/remediation code or before committing changes to the engine core.
allowed-tools: Read Grep Glob Bash
argument-hint: [path or glob, optional]
context: fork
---

# /remediation-audit — Engine Safety + Determinism Check

Delegate to the `remediation-safety-auditor` and `remediation-determinism-checker` agents.

## Scope

- If `$ARGUMENTS` is empty: current `git diff HEAD`.
- Otherwise: the path or glob in `$ARGUMENTS`.

## Workflow

1. Collect the scope (diff or files).
2. Invoke both agents with that scope as input:
   - `remediation-safety-auditor` — confirms the engine only emits commands, never executes.
   - `remediation-determinism-checker` — confirms commands come from pure `build_*` functions
     with no LLM / randomness.
3. Relay both verdicts directly. Do not paraphrase findings.
