---
paths:
  - "app/providers/**/remediation.py"
  - "app/detectors/**/*.py"
---

# Remediation Determinism Rules

> Every decommission command is produced by a pure, named `build_*` function. No LLM, no
> randomness, no time-based values in the command-generation path.

A command that decommissions a cloud resource must be reproducible and auditable. The same
`Resource` must always yield the same command string, byte for byte. This is what makes the
output trustworthy enough for a human to paste into a privileged shell.

## The three required pieces

Every remediation builder must be:

1. **Named** — a `build_*` function (e.g. `build_decommission_cmd`, `build_delete_volume_cmd`),
   not an inline f-string in a router or service.
2. **Pure** — takes the normalized `Resource` (and only that) and returns a `str`. No I/O, no
   DB, no network, no `boto3`.
3. **Deterministic** — no `random`, no `uuid`, no `datetime.now()`, no environment lookups. The
   command is a function of the resource fields alone.

## No LLM in the command path

The decommission command is **never** assembled, completed, or "cleaned up" by an LLM. Forbidden
imports anywhere in the remediation/detector path: `anthropic`, `openai`, `boto3` Bedrock
runtime, `langchain`, or any HTTP call to a model endpoint.

LLMs may only:

- Produce a human-readable *rationale* or *explanation* attached to a finding for display.
- Suggest which findings to prioritize.

These outputs are advisory and never become part of the executable command string.

## Forbidden

- Inline command construction in a router/service (must go through a `build_*` function).
- Random or time-based values inside a command.
- Any model call on the path that produces `findings.decommission_command`.

## Audit

The `remediation-determinism-checker` agent enforces this rule.
