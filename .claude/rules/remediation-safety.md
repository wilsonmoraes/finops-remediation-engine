---
paths:
  - "app/providers/**/*.py"
  - "app/detectors/**/*.py"
  - "app/modules/remediation/**/*.py"
  - "app/modules/ingest/**/*.py"
---

# Remediation Safety Rules

> The engine emits decommission commands as **data**. It never executes a mutating cloud call.
> A generated command is something a human reviews and runs — not something this service runs.

This is the single most important invariant of the project. A cost optimizer that can delete
cloud resources on its own is a liability, not a tool.

## The rule

The whole code path from ingest → detection → remediation produces **strings**. No layer in
that path may:

1. Construct a cloud SDK client that performs a mutation. Forbidden symbols anywhere in
   `app/providers/**`, `app/detectors/**`, and the `ingest` / `remediation` modules:
   `boto3.client`, `boto3.resource`, and any call matching `delete_*`, `terminate_*`,
   `release_*`, `deregister_*`, `stop_*`, `modify_*` on a cloud client.
2. Make an outbound network request to a cloud control-plane endpoint (`httpx`, `requests`,
   `urllib.request` against an AWS/Azure host).
3. Shell out to the cloud CLI (`subprocess` running `aws`/`az`).

## Generated commands are inert text

`build_decommission_cmd(resource) -> str` returns, for example:

```
aws ec2 delete-volume --volume-id vol-0abc123 --region us-east-1
```

That string is persisted in the `findings.decommission_command` column and surfaced in the API
and dashboard with a copy button. The architect (a human) runs it in their own authenticated
shell after reviewing it. The engine's responsibility ends at producing a correct, copy-pasteable
command.

## Dry-run by default

Every generated command targets a single, explicitly-identified resource (by id + region). The
engine never produces a wildcard, a `--recursive`, or a batch decommission. One finding → one
resource → one command.

## Allowed

- **Reading** exported files the user uploaded (CSV/JSON). That is the only input.
- Building and storing command strings.
- Read-only cloud SDK calls are *also* out of scope for the MVP — the engine works purely on
  uploaded exports, so it needs no cloud credentials at all.

## Audit

The `remediation-safety-auditor` agent enforces this rule. Run it before any commit touching the
provider, detector, ingest, or remediation code.
