"""SQL for the ``ingest_runs`` table."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from app import db


def insert(source_filename: str, provider: str) -> int:
    """Create an ingest run and return its id. Totals are filled in by :func:`finalize`."""

    return db.execute(
        """
        INSERT INTO ingest_runs (source_filename, provider, created_at)
        VALUES (:source_filename, :provider, :created_at)
        """,
        {
            "source_filename": source_filename,
            "provider": provider,
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


def finalize(run_id: int, resource_count: int, finding_count: int, total_waste: float) -> None:
    """Record the counts and total monthly waste once persistence completes."""

    db.execute(
        """
        UPDATE ingest_runs
        SET resource_count = :resource_count,
            finding_count = :finding_count,
            total_monthly_waste = :total_waste
        WHERE id = :run_id
        """,
        {
            "run_id": run_id,
            "resource_count": resource_count,
            "finding_count": finding_count,
            "total_waste": total_waste,
        },
    )


def get(run_id: int) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM ingest_runs WHERE id = :id", {"id": run_id})


def list_recent(limit: int = 50) -> list[sqlite3.Row]:
    return db.query_all("SELECT * FROM ingest_runs ORDER BY id DESC LIMIT :limit", {"limit": limit})
