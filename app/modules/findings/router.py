"""HTTP boundary for querying findings and the portfolio summary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.modules.findings import service
from app.modules.findings.schemas import FindingOut, SummaryOut

router = APIRouter(tags=["findings"])


@router.get("/summary", response_model=SummaryOut)
async def summary() -> SummaryOut:
    """Portfolio totals: monthly/annual waste, risk score, severity + rule breakdowns."""

    return service.get_summary()


@router.get("/findings", response_model=list[FindingOut])
async def list_findings(
    severity: str | None = Query(None, description="high | medium | low"),
    rule: str | None = Query(None, description="filter by detection rule"),
    min_waste: float = Query(0.0, ge=0, description="minimum monthly waste in USD"),
) -> list[FindingOut]:
    """List detected waste, highest monthly waste first."""

    return service.list_findings(severity=severity, rule=rule, min_waste=min_waste)


@router.get("/findings/{finding_id}", response_model=FindingOut)
async def get_finding(finding_id: int) -> FindingOut:
    """One finding with its decommission command."""

    try:
        return service.get_finding(finding_id)
    except service.FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
