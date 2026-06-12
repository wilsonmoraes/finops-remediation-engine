# Audit Log — Vibe Coding Workflow

Per the "2026 New Hire Challenge" Phase 3 rules, this file records every architect prompt used
to build this project. The human directs; the AI agent (Claude Code) writes all code. No manual
edits were made to the source.

**Project:** Cloud Cost Optimizer & Remediation Engine (Project 1 — FinOps)
**Agent:** Claude Code (Opus 4.8)
**Timer started:** turn 1 of this session.

---

## Required Initial Execution Prompt (from the challenge brief)

> Lead Architect mode: ON. We are building a Python-based, API-first **Cloud Cost Optimizer &
> Remediation Engine** using a free database and a dashboard.
>
> Rules:
> - **No Manual Edits:** You provide all logic and fixes. I will not edit any code.
> - **Audit Log:** You must maintain a file named prompts.md. After every turn, update that file
>   (or provide the text block) with the prompt I just used.
> - **Time-Check:** Start a timer. Goal is an MVP in 4-6 hours (Max window: 16h). Report
>   'Elapsed Time' at the end of every response. Acknowledge and let's start.

---

## Turn 1 — Project selection, standard alignment, repo + DB choice

> Lê a tarefa que tenho pra fazer [2026 New Hire Challenge]. Eu escolho essa opção Project 1:
> Cloud Cost Optimizer & Remediation Engine. Você pode olhar no fluxvia-platform todas as specs
> e rules e tudo que tem lá nessa pasta em .claude e copiar pra esse projeto pra a gente seguir
> o padrão, sem sofrimento. Você pode usar o gh pra criar um repo público em meu nome. O banco
> eu prefiro sqlite porque não precisaria configurar nada.

Clarifying answers given by the architect:
- Cloud provider scope: **AWS-first**, core provider-neutral (Azure pluggable later).
- Dashboard: **server-rendered HTMX + Jinja2** (one FastAPI service, zero node build).
- `.claude` rules: **adapt to FinOps** (keep meta-pattern, rewrite tenant/partner rules).
- Repo name: **finops-remediation-engine** (public, on the architect's GitHub).

### Agent execution (turn 1, autonomous build)

The agent then built the MVP end to end from the directives above, with no manual edits by the
architect:

1. Ported the `.claude` governance from the reference standard, adapted to FinOps: golden-rule
   pre-commit floor, path-scoped rules (python-conventions, layering, schema-canonical,
   remediation-safety, remediation-determinism, provider-neutral), auditor agents, git-gate hooks.
2. Built the pure core: normalized `Resource` shape, AWS parser (JSON + CSV), deterministic
   `build_*` decommission-command builders, five detection rules + engine.
3. Built the API + persistence: SQLite schema (`db/init_db.sql`), repos, and the ingest /
   findings / remediation modules (router/schemas/service split).
4. Built the server-rendered dashboard (HTMX + Jinja + Chart.js): waste KPIs, risk score,
   waste-by-rule chart, findings table with copy-command buttons.
5. Greened the floor: strict gate, layering gate, docs-language gate, ruff, black,
   pyright (strict, 0 errors), and 25 passing tests. Verified end to end against the running
   server (JSON + CSV ingest, summary, command output, dashboard render).
6. Published the public repository via `gh`.
