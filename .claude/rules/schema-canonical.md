---
paths:
  - "db/init_db.sql"
  - "app/repos/**/*.py"
  - "app/**/repo.py"
---

# Schema Canonical Source

## The rule

`db/init_db.sql` is the **single source of truth** for the database schema. It is idempotent
(`CREATE TABLE IF NOT EXISTS ...`) and recreated locally. There is no Alembic, no ORM-managed
schema, no `Base.metadata.create_all`.

## When you change a table

1. Edit `db/init_db.sql` first.
2. Reseed locally: delete the SQLite file and run `python scripts/init_db.py`.
3. Update repo code to match.
4. Run the `schema-sync-checker` agent to verify no drift.

## Naming

- Tables: `snake_case`, plural (`resources`, `findings`, `ingest_runs`).
- Columns: `snake_case`. Booleans prefixed `is_` / `has_`.
- Foreign keys: `<other_table_singular>_id`.
- Timestamps: `created_at`, `updated_at` (ISO-8601 `TEXT` in SQLite).

## SQLite specifics

- Types are SQLite affinities: `TEXT`, `INTEGER`, `REAL`. Money is `REAL` (monthly USD).
- Foreign keys need `PRAGMA foreign_keys = ON` per connection — set it in `app/db.py`.
- Booleans are `INTEGER` (0/1). Tags / raw payloads are `TEXT` holding JSON.

## Forbidden

- Alembic migrations. Do not propose them.
- ORM-only schema. The canonical script is the history.
- Schema definitions split across multiple files.

## Why no Alembic

Schema is maintained by editing `db/init_db.sql` and reseeding. The MVP does not need migration
history; the canonical script is the history. This is a conscious choice.
