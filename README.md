# FinOps Remediation Engine

A Python, API-first **Cloud Cost Optimizer & Remediation Engine**. It ingests AWS
billing/inventory exports (JSON or CSV), detects orphaned and idle resources, estimates the
monthly waste, and generates the **exact AWS CLI command** to decommission each one — surfaced
through a REST API and a server-rendered dashboard.

> Built for the 2026 New Hire "Vibe Coding" challenge (Project 1 — FinOps). The architect
> directed; the AI agent wrote every line. The full prompt audit log is in
> [`prompts.md`](prompts.md).

## What it does

1. **Ingest** an AWS export (`POST /ingest`). Two shapes are supported, both carrying the same
   normalized columns: an inventory **JSON** list, or a Cost-and-Usage-Report-style **CSV** with
   `tag:<Key>` columns.
2. **Detect** waste with pure rules: unattached EBS volumes, stopped/idle EC2 instances,
   unassociated Elastic IPs, idle load balancers, stale snapshots.
3. **Remediate** — for each finding it builds the precise, single-resource decommission command
   (e.g. `aws ec2 delete-volume --volume-id vol-0abc --region us-east-1`).
4. **Visualize** — a dashboard shows monthly/annual waste, a severity-weighted risk score, waste
   by rule (Chart.js), and a findings table with copy-to-clipboard commands.

### Safety first

The engine **never executes** a cloud mutation and **never connects** to a cloud account. It
works purely on uploaded export files and emits commands as inert text for a human to review and
run. This invariant is enforced by a rule (`.claude/rules/remediation-safety.md`) and an auditor
agent — see [Governance](#governance).

## Quick start

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -e ".[dev]"   # Windows; use .venv/bin on macOS/Linux
python scripts/init_db.py
.venv/Scripts/python -m uvicorn app.main:app --reload
```

Then:

- Dashboard: <http://localhost:8000/>
- API docs (OpenAPI): <http://localhost:8000/docs>

Ingest the bundled sample and inspect the results:

```bash
curl -F "file=@samples/aws_inventory.json" http://localhost:8000/ingest
curl http://localhost:8000/summary
curl http://localhost:8000/findings
curl http://localhost:8000/findings/1/command.txt
```

## Run against a live AWS account (read-only, optional)

The engine itself is file-based and needs no cloud credentials. To scan a real account, an
**optional** read-only collector turns a live inventory into an export the engine ingests:

```bash
aws sts get-caller-identity                                   # confirm the target account
python scripts/collect_aws_inventory.py --regions us-east-1   # or omit --regions for all enabled
curl -F "file=@data/aws_live_inventory.json" http://localhost:8000/ingest
```

`collect_aws_inventory.py` runs only `aws ... describe-*` calls — it never mutates or deletes
anything. Costs are best-effort estimates (no Cost-and-Usage-Report). Output lands in `data/`
(gitignored), so live account data never enters the repo. Scope: EC2-family (EBS, EC2, Elastic
IP, snapshots) plus ELBv2 — not Lambda/RDS/S3/CloudFront.

## API

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/ingest` | Upload an export; parse, detect, persist; returns a summary |
| `GET`  | `/summary` | Totals: monthly/annual waste, risk score, severity + rule breakdown |
| `GET`  | `/findings` | List findings (`?severity=`, `?rule=`, `?min_waste=`) |
| `GET`  | `/findings/{id}` | One finding with its decommission command |
| `GET`  | `/findings/{id}/command.txt` | Raw command string, ready to copy |
| `GET`  | `/` | Server-rendered dashboard |
| `GET`  | `/healthz` | Liveness probe |

## Architecture

```
app/
  main.py            FastAPI app: API routers + dashboard + static
  db.py              the one SQLite wrapper
  config.py          settings (DB path, idle thresholds)
  modules/<name>/    router.py + schemas.py + service.py (+ repo.py)
  repos/<table>.py   cross-module SQL, one file per table
  providers/<name>/  parser.py (export -> Resource) + remediation.py (Resource -> command)
  detectors/         pure rules.py + engine.py
db/init_db.sql       canonical SQLite schema (idempotent)
scripts/             init_db + gate scripts
samples/             example AWS exports
templates/ static/   dashboard (HTMX + Jinja + Chart.js)
```

The detector and remediation layers are **pure and provider-neutral**: rules key on a normalized
`Resource` shape, never on the provider name, so a second provider (Azure) drops in behind
`app/providers/azure/` without touching the core.

## Testing

```bash
.venv/Scripts/python -m pytest -q
```

Covers the parsers, the deterministic command builders, every detection rule, and the API
end-to-end via `TestClient` against a temporary SQLite database.

## Governance

This repo ships a Claude Code rule set under `.claude/` that mirrors a production engineering
standard, rewritten for this domain:

- **Pre-commit floor** (`/pre-commit` skill): a tokenizer strict gate, an AST layering gate, a
  docs-language gate, then `ruff` + `pyright` (strict) + `black`, then `pytest`.
- **Domain rules**: remediation-safety (emit, never execute), remediation-determinism (pure
  `build_*` functions, no LLM in the command path), provider-neutrality.
- **Auditor agents**: `remediation-safety-auditor`, `remediation-determinism-checker`,
  `schema-sync-checker`.

Run the gates directly:

```bash
python scripts/check_python_strict.py
python scripts/check_module_layering.py
python scripts/check_docs_language.py
```

## Submission checklist (challenge)

- [x] Public GitHub repository with all source code
- [x] `prompts.md` audit log of all instructions
- [x] AI-generated presentation deck ([`docs/deck.md`](docs/deck.md))
- [ ] Tagle.ai "Tag" output summary (architect's manual step)
- [x] No cloud resources to decommission — the engine works on exported files only and never
      provisions anything
