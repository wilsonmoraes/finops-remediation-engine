"""SQL for the ``resources`` table."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime

from app import db
from app.providers.base import Resource


def insert(run_id: int, resource: Resource) -> int:
    """Persist a normalized resource and return its row id."""

    return db.execute(
        """
        INSERT INTO resources (
            ingest_run_id, provider, account_id, region, service, resource_type,
            resource_id, state, monthly_cost, is_attached, last_activity_at,
            tags, raw, created_at
        ) VALUES (
            :ingest_run_id, :provider, :account_id, :region, :service, :resource_type,
            :resource_id, :state, :monthly_cost, :is_attached, :last_activity_at,
            :tags, :raw, :created_at
        )
        """,
        {
            "ingest_run_id": run_id,
            "provider": resource.provider,
            "account_id": resource.account_id,
            "region": resource.region,
            "service": resource.service,
            "resource_type": resource.resource_type,
            "resource_id": resource.resource_id,
            "state": resource.state,
            "monthly_cost": resource.monthly_cost,
            "is_attached": 1 if resource.attached else 0,
            "last_activity_at": resource.last_activity_at,
            "tags": json.dumps(resource.tags),
            "raw": json.dumps(resource.raw, default=str),
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


def get(resource_row_id: int) -> sqlite3.Row | None:
    return db.query_one("SELECT * FROM resources WHERE id = :id", {"id": resource_row_id})
