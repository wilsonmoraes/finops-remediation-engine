---
paths:
  - "app/**/*.py"
  - "scripts/**/*.py"
  - "tests/**/*.py"
---

# Python Conventions (FinOps Remediation Engine)

## Tooling

- Formatter: `black`
- Import sorter: `ruff` (isort rules, `I`)
- Linter: `ruff`
- Type checker: `pyright`

The `pre-commit` skill runs all of these before commit.

## Style

- Python 3.11+ idioms. Use `match` for tagged unions, `|` for unions in annotations, `Self`
  from `typing`.
- Prefer `from __future__ import annotations` for forward refs.
- Async by default in FastAPI handlers. Sync only when the library forces it (SQLite access is
  sync; keep it inside repos).
- Type every public function. `Any` is a smell; prefer `object` or a precise type.

## Comments (strict, no exceptions)

- **Never write inline comments** (`# something`). The hash-comment syntax is reserved for
  tooling pragmas only — `# type: ignore`, `# pyright: ignore[...]`, `# pragma: no cover`,
  `#!/usr/bin/env ...` shebangs, `# -*- coding: ... -*-` encoding declarations. Everything else
  gets removed.
- **When something needs explanation, write it in a docstring.** Module docstring for file-wide
  context, class docstring for class invariants, function docstring for the why-not-what.
- **Do not annotate sections of code with `# ---- foo ----` banners.** Extract a function
  instead; the function name and docstring are the banner.
- Removing a comment is preferred to keeping one that's "kind of useful". If the code can't be
  understood without the prose, that's a signal to rename a variable or split the function.

## Imports

- No wildcard imports.
- Standard library, third-party, first-party — three groups separated by blank lines.
- Absolute imports only.

## Errors

- Raise specific exceptions, never bare `Exception`.
- `HTTPException` only at the route boundary; raise domain exceptions inside repos/services and
  translate at the boundary.
- Never `except Exception: pass`. The `check_python_strict.py` gate bans `except Exception` and
  `# noqa` outright — narrow the catch instead of suppressing.

## Logging

- `logging.getLogger(__name__)`. No `print` in committed code (except CLI scripts under
  `scripts/` that are explicitly user-facing tools).

## Tests

- `pytest`, not `unittest.TestCase`.
- Fixtures in `conftest.py` at the closest reasonable scope.
- Pure detector/remediation logic is tested without a DB or network.
- API modules are tested via FastAPI `TestClient` against a temp SQLite file.

## Out of scope here

- Code layering (router/schemas/service/repo) — see `layering.md`
- Remediation safety — see `remediation-safety.md`
- Remediation determinism — see `remediation-determinism.md`
- Provider neutrality — see `provider-neutral.md`
- Schema canonical source — see `schema-canonical.md`
