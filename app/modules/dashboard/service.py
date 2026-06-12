"""Build the view context for the dashboard from the findings module."""

from __future__ import annotations

from typing import Any

from app.modules.findings import service as findings_service
from app.modules.ingest import service as ingest_service
from app.modules.ingest.schemas import IngestSummary


def handle_upload(filename: str, content: bytes, provider: str) -> IngestSummary:
    """Ingest an uploaded export on behalf of the dashboard form."""

    return ingest_service.run_ingest(filename, content, provider)


def build_context() -> dict[str, Any]:
    """Assemble the KPIs, severity/rule breakdowns, and findings table rows."""

    summary = findings_service.get_summary()
    findings = findings_service.list_findings(severity=None, rule=None, min_waste=0.0)
    severity_order = ["high", "medium", "low"]
    severity_rows = [
        {
            "severity": sev,
            "count": summary.by_severity[sev].count if sev in summary.by_severity else 0,
            "waste": summary.by_severity[sev].waste if sev in summary.by_severity else 0.0,
        }
        for sev in severity_order
    ]
    return {
        "summary": summary,
        "findings": findings,
        "severity_rows": severity_rows,
        "rule_rows": summary.by_rule,
        "risk_band": _risk_band(summary.risk_score),
    }


def _risk_band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"
