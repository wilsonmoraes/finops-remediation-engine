"""Ingest orchestration: parse → detect → persist.

This is the one place the pipeline is wired end to end. It reads settings for the
detection thresholds, stamps the run with today's date as the "as of" reference,
and persists resources before findings so each finding can reference its row.
"""

from __future__ import annotations

from datetime import date

from app.config import get_settings
from app.detectors.engine import detect
from app.detectors.rules import RuleConfig
from app.modules.ingest.schemas import IngestSummary
from app.providers import get_provider
from app.repos import findings as findings_repo
from app.repos import ingest_runs
from app.repos import resources as resources_repo


def run_ingest(filename: str, content: bytes, provider_name: str) -> IngestSummary:
    """Parse an export, run detection, persist everything, and return the summary."""

    provider = get_provider(provider_name)
    parsed = provider.parse(filename, content)

    settings = get_settings()
    cfg = RuleConfig(
        as_of=date.today(),
        idle_vm_days=settings.idle_vm_days,
        stale_snapshot_days=settings.stale_snapshot_days,
    )
    detected = detect(parsed, provider, cfg)

    run_id = ingest_runs.insert(filename, provider_name)
    row_id_by_resource: dict[int, int] = {}
    for resource in parsed:
        row_id_by_resource[id(resource)] = resources_repo.insert(run_id, resource)

    total_waste = 0.0
    for finding in detected:
        findings_repo.insert(run_id, row_id_by_resource[id(finding.resource)], finding)
        total_waste += finding.monthly_waste

    ingest_runs.finalize(run_id, len(parsed), len(detected), round(total_waste, 2))

    return IngestSummary(
        run_id=run_id,
        provider=provider_name,
        source_filename=filename,
        resource_count=len(parsed),
        finding_count=len(detected),
        total_monthly_waste=round(total_waste, 2),
    )
