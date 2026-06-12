"""HTTP boundary for ingesting cloud exports."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.modules.ingest import service
from app.modules.ingest.schemas import IngestSummary
from app.providers.base import ExportParseError

router = APIRouter(tags=["ingest"])


@router.post("/ingest", response_model=IngestSummary)
async def ingest(
    file: UploadFile = File(..., description="AWS billing/inventory export (.json or .csv)"),
    provider: str = Form("aws"),
) -> IngestSummary:
    """Upload an export, detect orphaned/idle resources, and persist the findings."""

    content = await file.read()
    try:
        return service.run_ingest(file.filename or "export", content, provider)
    except ExportParseError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
