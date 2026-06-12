# FinOps Remediation Engine — Solution Deck

A Markdown presentation deck for the 2026 New Hire Vibe Coding Challenge, Project 1.
Render with any Markdown slide tool (Marp, reveal.js, VS Code) — each `---` is a slide.

---

## 1. The problem

Cloud bills leak money through **orphaned resources** nobody owns anymore:

- Disks detached from terminated instances, still billing for storage.
- VMs stopped "temporarily" months ago, still holding addresses and volumes.
- Elastic IPs and load balancers serving nothing, billed by the hour.
- Snapshots from a project that shipped two years ago.

FinOps teams find these by hand, in spreadsheets. It does not scale.

---

## 2. The solution

An **API-first Cloud Cost Optimizer & Remediation Engine**:

> Ingest billing/inventory exports → detect orphaned/idle resources → estimate the waste →
> generate the exact decommission command → visualize risk.

- Python + FastAPI, SQLite (zero-config), HTMX/Jinja dashboard.
- AWS-first, with a provider-neutral core so Azure plugs in later.

---

## 3. Architecture (vibe-coded, layered on purpose)

```
ingest → normalize (Resource) → detect (pure rules) → remediate (deterministic cmd) → persist → dashboard
```

- **Pure core**: detectors and command builders are side-effect-free and deterministic.
- **Layered**: router / schemas / service / repo, enforced by an AST gate.
- **Provider-neutral**: rules key on a normalized shape, never on `provider == "aws"`.

---

## 4. The safety invariant

The engine **only emits commands**. It never connects to a cloud account and never executes a
deletion.

- Works purely on uploaded export files — needs no cloud credentials.
- Each command targets one explicitly-named resource. No wildcards, no batches.
- A human reviews each command and runs it in their own authenticated shell.

Enforced by a rule and an auditor agent, not just a promise.

---

## 5. Detection rules (MVP)

| Rule | Signal | Severity |
|---|---|---|
| Unattached EBS volume | `state=available`, not attached | high |
| Idle EC2 instance | stopped, or running + idle past threshold | high |
| Unassociated Elastic IP | not associated | medium |
| Idle load balancer | no registered targets | medium |
| Stale snapshot | unattached + older than 90 days | low |

Each rule is a pure function `Resource -> Finding | None`, independently unit-tested.

---

## 6. The dashboard

- KPIs: monthly waste, annualized waste, finding count, **risk score** (0–100).
- Risk score = severity-weighted share of at-risk spend (size-independent).
- Chart.js bar of waste by rule.
- Findings table with one-click **copy command**.

---

## 7. Engineering rigor

A Claude Code governance layer (`.claude/`) gates every commit:

- Tokenizer strict gate (no `noqa`, no broad `except`).
- AST layering gate (purity of detectors/remediation, router/service boundaries).
- `ruff` + `pyright --strict` + `black`, then `pytest`.
- Domain auditor agents for safety + determinism.

25 tests green: parsers, command builders, every rule, full API flow.

---

## 8. Result & next steps

- One command from a raw export to a prioritized, copy-pasteable remediation plan.
- **Next**: Azure provider adapter, scheduled ingests, a "mark remediated" workflow, and an
  optional read-only verification pass against a live account.

Repo + full prompt audit log: see `README.md` and `prompts.md`.
