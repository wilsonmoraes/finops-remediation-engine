-- Canonical schema for the FinOps Remediation Engine (SQLite).
--
-- This file is the single source of truth for the database. It is idempotent:
-- running it against an existing database makes no destructive change. There is
-- no Alembic; schema evolution = edit this file and reseed (delete the .db file
-- and re-run scripts/init_db.py).

PRAGMA foreign_keys = ON;

-- One row per uploaded export file. Groups the resources and findings produced
-- by a single ingest so the dashboard can show "this report found X waste".
CREATE TABLE IF NOT EXISTS ingest_runs (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    source_filename      TEXT    NOT NULL,
    provider             TEXT    NOT NULL,
    resource_count       INTEGER NOT NULL DEFAULT 0,
    finding_count        INTEGER NOT NULL DEFAULT 0,
    total_monthly_waste  REAL    NOT NULL DEFAULT 0,
    created_at           TEXT    NOT NULL
);

-- Normalized cloud resources parsed from an export. Provider-native vocabulary
-- is mapped onto these provider-agnostic columns by the parser, so the detector
-- core never needs to know which cloud a row came from.
CREATE TABLE IF NOT EXISTS resources (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_run_id     INTEGER NOT NULL REFERENCES ingest_runs(id) ON DELETE CASCADE,
    provider          TEXT    NOT NULL,
    account_id        TEXT    NOT NULL,
    region            TEXT    NOT NULL,
    service           TEXT    NOT NULL,
    resource_type     TEXT    NOT NULL,
    resource_id       TEXT    NOT NULL,
    state             TEXT    NOT NULL,
    monthly_cost      REAL    NOT NULL DEFAULT 0,
    is_attached       INTEGER NOT NULL DEFAULT 0,
    last_activity_at  TEXT,
    tags              TEXT    NOT NULL DEFAULT '{}',
    raw               TEXT    NOT NULL DEFAULT '{}',
    created_at        TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resources_ingest_run ON resources(ingest_run_id);
CREATE INDEX IF NOT EXISTS idx_resources_type ON resources(resource_type);

-- One row per orphaned/idle resource a detection rule flagged, with the exact
-- decommission command a human can review and run. The command is inert data:
-- the engine never executes it.
CREATE TABLE IF NOT EXISTS findings (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    ingest_run_id         INTEGER NOT NULL REFERENCES ingest_runs(id) ON DELETE CASCADE,
    resource_id           INTEGER NOT NULL REFERENCES resources(id) ON DELETE CASCADE,
    rule                  TEXT    NOT NULL,
    severity              TEXT    NOT NULL,
    monthly_waste         REAL    NOT NULL DEFAULT 0,
    risk_score            INTEGER NOT NULL DEFAULT 0,
    rationale             TEXT    NOT NULL,
    decommission_command  TEXT    NOT NULL,
    status                TEXT    NOT NULL DEFAULT 'open',
    created_at            TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_findings_ingest_run ON findings(ingest_run_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON findings(severity);
CREATE INDEX IF NOT EXISTS idx_findings_resource ON findings(resource_id);
