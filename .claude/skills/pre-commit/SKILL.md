---
name: pre-commit
description: Run the mandatory review pipeline before any commit. Use whenever the user is about to commit, says "ready to commit", or asks for a final check. Per CLAUDE.md golden rule.
allowed-tools: Bash Read Grep Glob
argument-hint: [--staged|--branch]
model: sonnet
---

# /pre-commit — Mandatory Review Pipeline

Per CLAUDE.md golden rule, no commit ships without this pipeline returning SHIP and the suite
green.

## Step 1: Determine scope

- Default (no args): staged + unstaged — `git diff HEAD`
- `--staged`: staged only — `git diff --staged`
- `--branch`: branch vs main — `git diff main...HEAD`

## Step 2: Snapshot

!`git status --short`

## Step 3: Mechanical floor — strict + layering + docs-lang + ruff + pyright + black

Run before the LLM-driven plugins so cheap, deterministic failures surface first. Each command
must finish at zero before the verdict can be SHIP.

!`python scripts/check_python_strict.py`
!`python scripts/check_module_layering.py`
!`python scripts/check_docs_language.py`
!`python -m ruff check app scripts tests`
!`python -m pyright`
!`python -m black --check --line-length 100 app scripts tests`

- `check_python_strict.py` bans `# noqa` (any form) and `except Exception:` / `except
  BaseException:`. Narrow the catch instead of suppressing. Bypass: `FINOPS_PY_STRICT_BYPASS=1`.
- `check_module_layering.py` enforces the per-module split (router HTTP-only, no `app.db` in
  routers, no `fastapi` in services/repos) and the purity of `detectors/` and
  `providers/*/remediation.py` (no `app.db`, no `boto3`/network, no LLM). Bypass:
  `FINOPS_MODULE_LAYERING_BYPASS=1`.
- `check_docs_language.py` keeps markdown docs in en-US. Bypass: `FINOPS_DOCS_LANG_BYPASS=1`.
- ruff config enables BLE, the E/F/I/B/UP/N/SIM/ARG/ERA/RUF/C90/RET set, and N818. Pyright runs
  in strict mode. Any non-zero exit is a blocker.

## Step 4: Run the plugins IN PARALLEL

Invoke in a single message:

1. `code-review` skill — bugs in the current local diff, plus the three domain invariants
   (remediation-safety, remediation-determinism, provider-neutrality).
2. `code-simplifier:code-simplifier` agent — dead branches, no-op defensive code.
3. `pyright-lsp` — type/import/undefined-symbol issues.

For diffs touching `app/providers/**`, `app/detectors/**`, or the ingest/remediation modules,
also invoke the `remediation-safety-auditor` and `remediation-determinism-checker` agents.

## Step 5: Tests

!`python -m pytest -q`

## Step 6: Verdict

Aggregate and render:

- **SHIP** — mechanical floor clean + plugins/agents clean + pytest green.
- **FIX** — list every finding grouped by tool, with `file:line — issue`.

## Step 7: Mark state

After the verdict is rendered, write the state file so the git-gate hook will allow
`git commit` / `git push`:

!`powershell -NoProfile -ExecutionPolicy Bypass -File .claude/hooks/mark-precommit-ok.ps1 -Verdict <SHIP|FIX>`

Pass the actual verdict literal. The state is keyed by the diff hash and expires after 10
minutes, so changes after this point require a re-run.

## Step 8: Confirmation

If SHIP, ask explicitly: "Pipeline clean. Commit?" Wait for yes/no. Never run `git commit`
without explicit confirmation.
