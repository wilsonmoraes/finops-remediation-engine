"""HTTP boundary for the server-rendered dashboard."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.modules.dashboard import service
from app.providers.base import ExportParseError

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

router = APIRouter(tags=["dashboard"], include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the waste/risk dashboard."""

    context = {"request": request, **service.build_context()}
    return templates.TemplateResponse(request, "dashboard.html", context)


@router.get("/partials/findings", response_class=HTMLResponse)
async def findings_partial(request: Request) -> HTMLResponse:
    """HTMX partial: just the findings table (used to refresh after an upload)."""

    context = {"request": request, **service.build_context()}
    return templates.TemplateResponse(request, "_findings_table.html", context)


@router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    provider: str = Form("aws"),
) -> RedirectResponse:
    """Dashboard upload form target: ingest, then redirect back to the dashboard."""

    content = await file.read()
    try:
        service.handle_upload(file.filename or "export", content, provider)
    except (ExportParseError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(url="/", status_code=303)
