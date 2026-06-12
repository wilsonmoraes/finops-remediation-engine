"""HTTP boundary for the decommission command of a finding."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from app.modules.remediation import service
from app.modules.remediation.schemas import CommandOut

router = APIRouter(tags=["remediation"])


@router.get("/findings/{finding_id}/command", response_model=CommandOut)
async def get_command(finding_id: int) -> CommandOut:
    """The decommission command for a finding, as structured JSON."""

    try:
        return service.get_command(finding_id)
    except service.FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/findings/{finding_id}/command.txt", response_class=PlainTextResponse)
async def get_command_text(finding_id: int) -> str:
    """The raw command string, ready to copy into a shell."""

    try:
        return service.get_command(finding_id).decommission_command
    except service.FindingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
