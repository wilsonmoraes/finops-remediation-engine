"""FastAPI application entrypoint.

Wires the API routers (ingest, findings, remediation) and the server-rendered
dashboard, mounts static assets, and ensures the SQLite schema exists on startup.
The app is API-first: every JSON route is in the auto-generated OpenAPI at /docs;
the dashboard is a thin HTML view over the same services.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.db import init_schema
from app.modules.dashboard.router import router as dashboard_router
from app.modules.findings.router import router as findings_router
from app.modules.ingest.router import router as ingest_router
from app.modules.remediation.router import router as remediation_router

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
    """Apply the canonical schema before serving the first request."""

    init_schema()
    yield


app = FastAPI(
    title="FinOps Remediation Engine",
    version="0.1.0",
    summary="Detect orphaned AWS resources and emit decommission commands.",
    description=(
        "Upload an AWS billing/inventory export to detect orphaned and idle resources and "
        "generate the exact decommission command for each. The engine never executes a "
        "cloud mutation."
    ),
    lifespan=lifespan,
)

app.include_router(ingest_router)
app.include_router(findings_router)
app.include_router(remediation_router)
app.include_router(dashboard_router)

app.mount("/static", StaticFiles(directory=str(_STATIC_DIR)), name="static")


@app.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    """Liveness probe."""

    return {"status": "ok"}
