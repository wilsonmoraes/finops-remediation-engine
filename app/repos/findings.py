"""SQL for the ``findings`` table.

Reads join ``resources`` so a finding row carries its resource's identity (type,
id, region, tags) in one query — the dashboard and API never need a second hop.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from typing import TypedDict

from app import db
from app.detectors.engine import Finding


class SeverityAgg(TypedDict):
    count: int
    waste: float


class RuleAgg(TypedDict):
    rule: str
    count: int
    waste: float


class SummaryRaw(TypedDict):
    finding_count: int
    monthly_waste: float
    annual_waste: float
    by_severity: dict[str, SeverityAgg]
    by_rule: list[RuleAgg]


_SELECT = """
    SELECT
        f.id, f.ingest_run_id, f.rule, f.severity, f.monthly_waste, f.risk_score,
        f.rationale, f.decommission_command, f.status, f.created_at,
        r.provider, r.account_id, r.region, r.service, r.resource_type,
        r.resource_id, r.state, r.monthly_cost, r.is_attached, r.tags
    FROM findings f
    JOIN resources r ON r.id = f.resource_id
"""


def insert(run_id: int, resource_row_id: int, finding: Finding) -> int:
    return db.execute(
        """
        INSERT INTO findings (
            ingest_run_id, resource_id, rule, severity, monthly_waste, risk_score,
            rationale, decommission_command, status, created_at
        ) VALUES (
            :ingest_run_id, :resource_id, :rule, :severity, :monthly_waste, :risk_score,
            :rationale, :decommission_command, :status, :created_at
        )
        """,
        {
            "ingest_run_id": run_id,
            "resource_id": resource_row_id,
            "rule": finding.rule,
            "severity": finding.severity,
            "monthly_waste": finding.monthly_waste,
            "risk_score": finding.risk_score,
            "rationale": finding.rationale,
            "decommission_command": finding.decommission_command,
            "status": "open",
            "created_at": datetime.now(UTC).isoformat(),
        },
    )


def get(finding_id: int) -> sqlite3.Row | None:
    return db.query_one(f"{_SELECT} WHERE f.id = :id", {"id": finding_id})


def list_filtered(
    severity: str | None = None,
    rule: str | None = None,
    min_waste: float = 0.0,
) -> list[sqlite3.Row]:
    """List findings, newest run first, filtered by the optional criteria."""

    clauses = ["f.monthly_waste >= :min_waste"]
    params: dict[str, object] = {"min_waste": min_waste}
    if severity:
        clauses.append("f.severity = :severity")
        params["severity"] = severity
    if rule:
        clauses.append("f.rule = :rule")
        params["rule"] = rule
    where = " AND ".join(clauses)
    return db.query_all(f"{_SELECT} WHERE {where} ORDER BY f.monthly_waste DESC, f.id DESC", params)


def summary() -> SummaryRaw:
    """Aggregate totals for the dashboard: waste, counts, severity + rule breakdowns."""

    totals = db.query_one("""
        SELECT
            COUNT(*) AS finding_count,
            COALESCE(SUM(monthly_waste), 0) AS monthly_waste,
            COALESCE(MAX(risk_score), 0) AS top_risk
        FROM findings
        """)
    by_severity = db.query_all("""
        SELECT severity, COUNT(*) AS n, COALESCE(SUM(monthly_waste), 0) AS waste
        FROM findings GROUP BY severity
        """)
    by_rule = db.query_all("""
        SELECT rule, COUNT(*) AS n, COALESCE(SUM(monthly_waste), 0) AS waste
        FROM findings GROUP BY rule ORDER BY waste DESC
        """)
    finding_count = int(totals["finding_count"]) if totals else 0
    monthly_waste = float(totals["monthly_waste"]) if totals else 0.0
    return SummaryRaw(
        finding_count=finding_count,
        monthly_waste=round(monthly_waste, 2),
        annual_waste=round(monthly_waste * 12, 2),
        by_severity={
            row["severity"]: SeverityAgg(count=int(row["n"]), waste=round(float(row["waste"]), 2))
            for row in by_severity
        },
        by_rule=[
            RuleAgg(rule=row["rule"], count=int(row["n"]), waste=round(float(row["waste"]), 2))
            for row in by_rule
        ],
    )
