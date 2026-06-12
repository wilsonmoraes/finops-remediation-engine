"""Request/response models for the findings module."""

from __future__ import annotations

from pydantic import BaseModel


class ResourceRef(BaseModel):
    """The resource a finding points at."""

    provider: str
    account_id: str
    region: str
    service: str
    resource_type: str
    resource_id: str
    state: str
    monthly_cost: float
    is_attached: bool
    tags: dict[str, str]


class FindingOut(BaseModel):
    """A detected piece of waste with its remediation command."""

    id: int
    ingest_run_id: int
    rule: str
    severity: str
    monthly_waste: float
    risk_score: int
    rationale: str
    decommission_command: str
    status: str
    resource: ResourceRef


class SeverityBucket(BaseModel):
    count: int
    waste: float


class RuleBucket(BaseModel):
    rule: str
    count: int
    waste: float


class SummaryOut(BaseModel):
    """Portfolio totals that drive the dashboard KPIs."""

    finding_count: int
    monthly_waste: float
    annual_waste: float
    risk_score: int
    by_severity: dict[str, SeverityBucket]
    by_rule: list[RuleBucket]
