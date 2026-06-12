# FinOps Remediation Engine — Claude Instructions

This file is auto-loaded by Claude Code (CLI, IDE, Web). It configures the assistant's
behavior for this repository in a way that is shared across developers.

The governance here is adapted from the Fluxvia platform standard. The *meta-pattern* is
preserved (golden-rule pre-commit floor, path-scoped rules, on-demand auditor agents); the
*domain content* is rewritten for FinOps — there is no multi-tenant or partner-sync concept
here. The three domain invariants are **remediation safety**, **remediation determinism**, and
**provider neutrality**.

## What this project is

A Python, API-first **Cloud Cost Optimizer & Remediation Engine**. It ingests AWS
billing/inventory exports (CSV/JSON), detects *orphaned* and *idle* resources (unattached
disks, stopped VMs, unassociated Elastic IPs, idle load balancers, stale snapshots), estimates
the monthly waste, and generates the **exact CLI command** needed to decommission each one. A
server-rendered dashboard (HTMX + Jinja2) visualizes the waste and a risk score. Storage is
SQLite (zero-config). The engine **never executes** a mutating cloud call — it only emits
commands for a human to review and run.

## Golden rule: review before commit (mandatory)

**Before any `git commit` on a non-trivial change, the floor below must finish at zero, in
this order. Skipping any layer is not allowed.**

### Mechanical floor (cheap, deterministic — must be zero)

1. **`scripts/check_python_strict.py`** — tokenizer gate that bans `# noqa` and
   `except Exception` / `except BaseException`. Narrow the catch; do not suppress. Bypass:
   `FINOPS_PY_STRICT_BYPASS=1`.
2. **`scripts/check_module_layering.py`** — AST gate enforcing the per-module split
   (router/schemas/service/repo) and the purity of `detectors/` and `providers/*/remediation.py`
   (no `app.db`, no network, no LLM). Bypass: `FINOPS_MODULE_LAYERING_BYPASS=1` (emergencies).
3. **`scripts/check_docs_language.py`** — keeps markdown docs in en-US. Bypass:
   `FINOPS_DOCS_LANG_BYPASS=1`.
4. **`ruff`** — `python -m ruff check app scripts tests`.
5. **`pyright`** in strict mode — `pyright` (config in `pyproject.toml`).
6. **`black --check`** — `python -m black --check --line-length 100 app scripts tests`.

### Semantic plugins (LLM-driven — must return SHIP)

7. **`code-review:code-review`** — bugs, remediation-safety (no mutating cloud calls),
   remediation-determinism (no LLM in command-gen), provider-neutrality, SQL injection,
   duplication against existing repos.
8. **`code-simplifier:code-simplifier`** — collapses dead branches, removes no-op defensive code.
9. **`pyright-lsp`** — re-checks the strict pyright run in the editor view.

### Tests (must be green)

10. `python -m pytest -q`.

Non-trivial = anything beyond a one-line typo/rename.

The `/pre-commit` skill (`.claude/skills/pre-commit/`) automates the whole pipeline.

## The three domain invariants

- **Remediation safety** (`.claude/rules/remediation-safety.md`): the engine emits CLI text as
  data; it never calls a mutating cloud API. No `boto3` client that performs `delete_*`,
  `terminate_*`, `release_*`, `deregister_*` in the request or detector path.
- **Remediation determinism** (`.claude/rules/remediation-determinism.md`): every decommission
  command is produced by a pure, named `build_*` function — `Resource -> str`. No LLM, no
  randomness, no time-based values in the command-generation path.
- **Provider neutrality** (`.claude/rules/provider-neutral.md`): core detectors and the API
  never branch on a provider-name literal (`provider == "aws"`). Provider specifics live behind
  `app/providers/<name>/`; the core keys on the normalized `Resource` shape.

## Code and product conventions

- **Language**: all code/identifiers/docs in **en-US**. User-facing dashboard copy may be
  pt-BR if the audience is the operator.
- **No AI self-reference in commits/PRs/docs**: no `Co-Authored-By: Claude...` or "Generated
  with Claude Code" lines.
- **Commit messages are short**: a single subject line, max 100 characters, no essay body.
- **No emojis** in code, docs, or templates unless explicitly requested.
- **No inline comments in Python** (`# something`). Hash-comments are reserved for tooling
  pragmas (`# type: ignore`, `# pragma: no cover`, shebangs, coding declarations). Explanations
  go in docstrings. See `.claude/rules/python-conventions.md`.
- **Canonical schema**: `db/init_db.sql` is the single source of truth (SQLite). No Alembic.
  See `.claude/rules/schema-canonical.md`.

## Structure

```
app/
  main.py                  — FastAPI app: API routers + dashboard + static/templates
  db.py                    — the ONE sqlite3 wrapper (execute helpers)
  config.py                — settings (DB path, idle thresholds)
  modules/<name>/          — router.py + schemas.py + service.py + repo.py (one folder per feature)
  repos/<table>.py         — cross-module SQL on a single table (resources, findings, ingest_runs)
  providers/<name>/        — provider adapters (parser.py + remediation.py); pure, no app.db
  detectors/               — pure orphan-detection rules (rules.py + engine.py)
db/init_db.sql             — canonical SQLite schema (idempotent)
scripts/check_*.py         — gate scripts (python-strict, module-layering, docs-language)
scripts/init_db.py         — apply db/init_db.sql
samples/                   — example AWS exports for demo + tests
templates/ static/         — Jinja + Chart.js dashboard assets
tests/                     — pytest mirror of app/
prompts.md                 — Vibe Coding audit log (challenge requirement)
```

## Vibe Coding workflow (challenge rules)

This repo is built under the "2026 New Hire Challenge" Vibe Coding rules:

- **No manual edits** — Claude provides all logic and fixes; the human is the architect.
- **Audit log** — `prompts.md` records every architect prompt, appended each turn.
- **Time-check** — elapsed time is reported each turn; MVP target 4–6h (max 16h).

## Pre-commit gate (enforcement)

The Claude Code hook (`.claude/settings.json` → `hooks.PreToolUse` on `Bash`) denies any
`git commit` / `git push` unless `.claude/state/precommit_ok.json` shows verdict=SHIP, age
< 10 min, and a diff hash matching the current `git diff HEAD`. The `/pre-commit` skill writes
this state via `.claude/hooks/mark-precommit-ok.ps1`. Bypass: `FINOPS_PRECOMMIT_BYPASS=1`.

## References

- `db/init_db.sql` — canonical schema.
- `.claude/rules/` — path-scoped rules (auto-loaded when Claude touches matching files).
- `README.md` — run + demo instructions.
