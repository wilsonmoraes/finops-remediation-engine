"""Request/response models for the ingest module."""

from __future__ import annotations

from pydantic import BaseModel


class IngestSummary(BaseModel):
    """Result of ingesting one export file."""

    run_id: int
    provider: str
    source_filename: str
    resource_count: int
    finding_count: int
    total_monthly_waste: float
