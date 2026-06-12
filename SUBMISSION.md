# Submission — 2026 New Hire Vibe Coding Challenge

**Candidate:** Wilson Moraes
**Project chosen:** Project 1 — Cloud Cost Optimizer & Remediation Engine (FinOps)
**Repository:** https://github.com/wilsonmoraes/finops-remediation-engine (public)

## Phase 1 — Tagle.ai "Tag"

**AI Readiness Type: THE NAVIGATOR** — with an Architect edge | Developing
**Projected stage:** Confident Operator

| Dimension | Score |
|---|---|
| Growth | 53 |
| Autonomy | 91 |
| Competence | 75 |
| Relatedness | 47 |
| Innovation | 66 |

**Placement:** Confident Operator — *Developing mindset · High skills*.

**Profile:** "Navigators refuse to follow the crowd. You think independently about how AI fits
into your world and chart your own course forward. This self-direction means you'll adapt on your
own terms, finding applications others overlook. Your Architect edge gives you the depth to back
up your instincts with real expertise."

**Next focus (per Tagle):** add depth — prompt patterns, evaluation habits, or a tool you've been
avoiding.

Source: tagle.ai/quiz result (directional projection from the 5-minute quiz; the full
conversational assessment may shift the stage).

## Phase 2 — Architecture

API-first, Python (FastAPI), SQLite (free-tier, zero-config), server-rendered HTMX + Jinja
dashboard. AWS-first with a provider-neutral core. The engine ingests AWS billing/inventory
exports (JSON/CSV), detects orphaned and idle resources, and generates the exact AWS CLI
decommission command for each — as inert text it never executes. See `README.md` and
`docs/deck.md`.

## Phase 3 — Vibe Coding workflow

Built end to end by the AI agent (Claude Code, Opus 4.8); no manual code edits by the architect.
Full prompt audit log: `prompts.md`. Engineering floor green: strict/layering/docs-language
gates, ruff, black, pyright (strict, 0 errors), 27 passing tests, plus safety + determinism
auditor agents (SHIP / DETERMINISTIC).

## Final submission checklist

- [x] Tagle.ai "Tag" output summary included (above)
- [x] Public GitHub repository with all source code
- [x] `prompts.md` audit log of all instructions
- [x] AI-generated presentation deck (`docs/deck.md`)
- [x] All cloud resources decommissioned / accounts closed — N/A: the engine works on uploaded
      export files and provisions nothing, so there is no live cloud environment to tear down
