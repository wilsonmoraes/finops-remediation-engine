"""Findings orchestration: map persisted rows to API models, compute the risk score."""

from __future__ import annotations

import json
import sqlite3

from app.modules.findings.schemas import (
    FindingOut,
    ResourceRef,
    RuleBucket,
    SeverityBucket,
    SummaryOut,
)
from app.repos import findings as findings_repo
from app.repos.findings import SeverityAgg

_SEVERITY_WEIGHT = {"high": 1.0, "medium": 0.6, "low": 0.3}


class FindingNotFoundError(LookupError):
    """Raised when a finding id does not exist."""


def list_findings(severity: str | None, rule: str | None, min_waste: float) -> list[FindingOut]:
    rows = findings_repo.list_filtered(severity=severity, rule=rule, min_waste=min_waste)
    return [_to_finding(row) for row in rows]


def get_finding(finding_id: int) -> FindingOut:
    row = findings_repo.get(finding_id)
    if row is None:
        raise FindingNotFoundError(f"finding {finding_id} not found")
    return _to_finding(row)


def get_summary() -> SummaryOut:
    raw = findings_repo.summary()
    return SummaryOut(
        finding_count=raw["finding_count"],
        monthly_waste=raw["monthly_waste"],
        annual_waste=raw["annual_waste"],
        risk_score=_risk_score(raw["by_severity"]),
        by_severity={
            sev: SeverityBucket(count=bucket["count"], waste=bucket["waste"])
            for sev, bucket in raw["by_severity"].items()
        },
        by_rule=[
            RuleBucket(rule=bucket["rule"], count=bucket["count"], waste=bucket["waste"])
            for bucket in raw["by_rule"]
        ],
    )


def _risk_score(by_severity: dict[str, SeverityAgg]) -> int:
    """Severity-weighted share of at-risk spend, 0-100.

    Independent of absolute size: a portfolio of mostly high-severity waste scores
    near 100, mostly low-severity near 30, and an empty portfolio scores 0.
    """

    total = sum(bucket["waste"] for bucket in by_severity.values())
    if total <= 0:
        return 0
    weighted = sum(
        _SEVERITY_WEIGHT.get(sev, 0.3) * bucket["waste"] for sev, bucket in by_severity.items()
    )
    return min(100, round(100 * weighted / total))


def _to_finding(row: sqlite3.Row) -> FindingOut:
    return FindingOut(
        id=int(row["id"]),
        ingest_run_id=int(row["ingest_run_id"]),
        rule=row["rule"],
        severity=row["severity"],
        monthly_waste=float(row["monthly_waste"]),
        risk_score=int(row["risk_score"]),
        rationale=row["rationale"],
        decommission_command=row["decommission_command"],
        status=row["status"],
        resource=ResourceRef(
            provider=row["provider"],
            account_id=row["account_id"],
            region=row["region"],
            service=row["service"],
            resource_type=row["resource_type"],
            resource_id=row["resource_id"],
            state=row["state"],
            monthly_cost=float(row["monthly_cost"]),
            is_attached=bool(row["is_attached"]),
            tags=json.loads(row["tags"]),
        ),
    )
