---
paths:
  - "app/**/*.py"
---

# Code Layering Contract (FinOps Remediation Engine)

> The router/schemas/service/repo split and the purity of `detectors/` and
> `providers/*/remediation.py` are enforced by `scripts/check_module_layering.py`
> (AST gate, in the pre-commit floor).

## API modules — `app/modules/<name>/`

At most four files per module. Each file has one job.

| File | What goes in | Allowed imports |
|---|---|---|
| `router.py` | Endpoints, dependency injection, exception translation | `fastapi`, the module's own `schemas` / `service`, `app.deps.*` |
| `schemas.py` | Pydantic request/response models, validators | `pydantic`, `typing`, `datetime` |
| `service.py` | Business orchestration, raises domain `*Error` exceptions | repos (`app.repos.*`, module's own `repo`), `app.detectors.*`, `app.providers.*` |
| `repo.py` | Module-private SQL (queries only this module uses) | `app.db`, stdlib |

Cross-module SQL lives in **`app/repos/<table>.py`** (one file per table: `resources.py`,
`findings.py`, `ingest_runs.py`). Before adding a query to a module's `repo.py`, search
`app/repos/` — most "look up X by Y" queries already exist.

Enforced rules:

1. `router.py` must not import `app.db`. Move the call into a repo.
2. `router.py` must not declare a `BaseModel` subclass. Move it to `schemas.py`.
3. `service.py` must not import `fastapi`. Domain exceptions cross the boundary, not
   `HTTPException`.
4. `repo.py` must not import `fastapi`. Repos stay HTTP-agnostic.

## Pure core — `app/detectors/` and `app/providers/<name>/`

These layers are **pure**: deterministic functions over the normalized `Resource` shape. They
are the heart of the engine and must stay free of side effects.

| Layer | What goes in | Allowed imports |
|---|---|---|
| `app/providers/base.py` | `Resource` dataclass + `Provider` protocol | stdlib, `dataclasses`, `typing` |
| `app/providers/<name>/parser.py` | export file (CSV/JSON) → `Resource[]` | stdlib (`csv`, `json`), `app.providers.base` |
| `app/providers/<name>/remediation.py` | `Resource` → decommission command string | stdlib, `app.providers.base` |
| `app/detectors/rules.py` | one pure function per orphan rule: `Resource -> Finding \| None` | `app.providers.base`, `app.detectors.engine` types |
| `app/detectors/engine.py` | run all rules over `Resource[]` → `Finding[]` | `app.detectors.rules`, `app.providers.*` |

Enforced rules (gate rules 5-7):

5. `app/detectors/**` must not import `app.db`, `fastapi`, `boto3`, `httpx`, `requests`,
   `anthropic`, `openai`. Pure logic only.
6. `app/providers/*/remediation.py` must not import `app.db`, `boto3`, `httpx`, `requests`,
   `anthropic`, `openai`. It builds command *strings*; it never executes them.
7. `app/providers/*/parser.py` must not import `app.db` or `fastapi`. Parsing is pure.

## Practical rules of thumb

- **Adding a new query?** First grep `app/repos/`. If the table already has a repo file, add the
  function there.
- **A new detection rule?** Add a pure `Resource -> Finding | None` function in
  `detectors/rules.py` and register it in `engine.py`. No I/O.
- **A new decommission command?** Add a `build_*` function in the provider's `remediation.py`.
  Pure string assembly only.

## Bypass

`FINOPS_MODULE_LAYERING_BYPASS=1` exists for emergencies only.

## Out of scope here

- Remediation safety — see `remediation-safety.md`
- Remediation determinism — see `remediation-determinism.md`
- Provider neutrality — see `provider-neutral.md`
- Pythonic style + comments — see `python-conventions.md`
- Schema canonical source — see `schema-canonical.md`
