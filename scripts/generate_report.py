"""Render a FinOps waste report (PDF) from a live or sample inventory snapshot.

This is a reporting helper, separate from the engine. It ingests an inventory
export through the engine in-process (FastAPI ``TestClient``), reads back the
``/summary`` and ``/findings`` results, and renders them as a single PDF for a
human reviewer. It performs no cloud calls and mutates nothing.

The engine's ``/summary`` and ``/findings`` endpoints aggregate the whole
database, so this script reflects every ingest the database holds, not only the
file passed here. Start from a fresh database (``python scripts/init_db.py``
against an empty ``data/finops.db``) so the report covers exactly one inventory.

Usage:
    python scripts/init_db.py
    python scripts/generate_report.py
    python scripts/generate_report.py --inventory data/aws_live_inventory.json \\
        --out reports/finops_aws_report.pdf --generated-on 2026-06-12
"""

from __future__ import annotations

import argparse
import datetime
import json
from collections import Counter
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.main import app

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_INVENTORY = _REPO_ROOT / "data" / "aws_live_inventory.json"
_DEFAULT_OUT = _REPO_ROOT / "reports" / "finops_aws_report.pdf"

_NAVY = colors.HexColor("#0b2545")
_ACCENT = colors.HexColor("#1d6fb8")
_LIGHT = colors.HexColor("#eef3f8")
_MUTED = colors.HexColor("#5a6b7b")
_OK = colors.HexColor("#1b7a43")


def _run_engine(inventory: Path) -> dict[str, Any]:
    client = TestClient(app)
    with inventory.open("rb") as handle:
        ingest = client.post(
            "/ingest",
            files={"file": (inventory.name, handle, "application/json")},
        )
    ingest.raise_for_status()
    summary = client.get("/summary")
    summary.raise_for_status()
    findings = client.get("/findings")
    findings.raise_for_status()
    return {
        "ingest": ingest.json(),
        "summary": summary.json(),
        "findings": findings.json(),
    }


def _inventory_meta(inventory: Path) -> dict[str, Any]:
    payload = json.loads(inventory.read_text(encoding="utf-8"))
    resources = payload.get("resources", [])
    accounts = sorted({str(r.get("account_id", "")) for r in resources if r.get("account_id")})
    regions = sorted({str(r.get("region", "")) for r in resources if r.get("region")})
    by_type = Counter(str(r.get("resource_type", "")) for r in resources)
    return {
        "resources": resources,
        "accounts": accounts,
        "regions": regions,
        "by_type": dict(by_type),
        "note": str(payload.get("_note", "")),
    }


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            textColor=_NAVY,
            fontSize=22,
            leading=26,
            spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            parent=base["Normal"],
            textColor=_MUTED,
            fontSize=10.5,
            leading=14,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            textColor=_NAVY,
            fontSize=13,
            spaceBefore=14,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["Normal"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#243240"),
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["Normal"],
            fontSize=8.5,
            leading=12,
            textColor=_MUTED,
        ),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=9, leading=12),
        "cellmono": ParagraphStyle(
            "cellmono",
            parent=base["Normal"],
            fontName="Courier",
            fontSize=8,
            leading=11,
        ),
    }


def _kpi_band(summary: dict[str, Any], resource_count: int, st: dict[str, ParagraphStyle]) -> Table:
    monthly = float(summary.get("monthly_waste", 0.0))
    annual = float(summary.get("annual_waste", 0.0))
    cells = [
        ("Resources scanned", str(resource_count)),
        ("Waste findings", str(summary.get("finding_count", 0))),
        ("Monthly waste", f"${monthly:,.2f}"),
        ("Annual waste", f"${annual:,.2f}"),
        ("Risk score", f"{summary.get('risk_score', 0)}/100"),
    ]
    value_style = ParagraphStyle(
        "kpival", parent=st["body"], fontSize=16, leading=18, textColor=_ACCENT, alignment=1
    )
    label_style = ParagraphStyle("kpilab", parent=st["small"], alignment=1, spaceBefore=2)
    row = [[Paragraph(v, value_style), Paragraph(k, label_style)] for k, v in cells]
    table = Table([[Table([[c[0]], [c[1]]]) for c in row]], colWidths=[34 * mm] * len(cells))
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), _LIGHT),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.white),
                ("INNERGRID", (0, 0), (-1, -1), 3, colors.white),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    return table


def _inventory_table(resources: list[dict[str, Any]], st: dict[str, ParagraphStyle]) -> Table:
    header = ["Type", "Resource ID", "Region", "State", "In use", "Est. $/mo"]
    rows: list[list[Any]] = [header]
    for r in resources:
        rows.append(
            [
                Paragraph(str(r.get("resource_type", "")), st["cell"]),
                Paragraph(str(r.get("resource_id", "")), st["cellmono"]),
                Paragraph(str(r.get("region", "")), st["cell"]),
                Paragraph(str(r.get("state", "")), st["cell"]),
                Paragraph("yes" if r.get("attached") else "no", st["cell"]),
                Paragraph(f"{float(r.get('monthly_cost', 0)):,.2f}", st["cell"]),
            ]
        )
    table = Table(rows, colWidths=[24 * mm, 52 * mm, 22 * mm, 26 * mm, 16 * mm, 22 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cdd8e3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _findings_block(findings: list[dict[str, Any]], st: dict[str, ParagraphStyle]) -> list[Any]:
    if not findings:
        ok = ParagraphStyle("ok", parent=st["body"], textColor=_OK, fontSize=11)
        return [
            Paragraph("No orphaned or idle resources detected.", ok),
            Spacer(1, 3),
            Paragraph(
                "Every scanned resource is in active use. There is no decommission action to take "
                "on this account at the time of the scan.",
                st["body"],
            ),
        ]
    header = ["Severity", "Rule", "$/mo", "Decommission command"]
    rows: list[list[Any]] = [header]
    for f in findings:
        rows.append(
            [
                Paragraph(str(f.get("severity", "")), st["cell"]),
                Paragraph(str(f.get("rule", "")), st["cell"]),
                Paragraph(f"{float(f.get('monthly_waste', 0)):,.2f}", st["cell"]),
                Paragraph(str(f.get("decommission_command", "")), st["cellmono"]),
            ]
        )
    table = Table(rows, colWidths=[20 * mm, 40 * mm, 16 * mm, 86 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), _NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _LIGHT]),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cdd8e3")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return [table]


def build(inventory: Path, out: Path, generated_on: str, subtitle: str) -> Path:
    meta = _inventory_meta(inventory)
    result = _run_engine(inventory)
    summary = result["summary"]
    findings = result["findings"]
    st = _styles()

    out.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(out),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=16 * mm,
        title="FinOps Remediation Engine - AWS Account Report",
        author="FinOps Remediation Engine",
    )

    account = ", ".join(meta["accounts"]) or "unknown"
    region_count = len(meta["regions"])
    story: list[Any] = []
    story.append(Paragraph("FinOps Remediation Engine", st["title"]))
    story.append(Paragraph(subtitle, st["subtitle"]))
    story.append(Spacer(1, 8))
    story.append(
        Paragraph(
            f"Account <b>{account}</b> &nbsp;|&nbsp; {len(meta['resources'])} resource(s) across "
            f"{region_count} region(s) with resources &nbsp;|&nbsp; generated {generated_on}",
            st["small"],
        )
    )
    story.append(Spacer(1, 10))
    story.append(_kpi_band(summary, len(meta["resources"]), st))

    story.append(Paragraph("Result", st["h2"]))
    story.extend(_findings_block(findings, st))

    story.append(Paragraph("Scanned inventory", st["h2"]))
    if meta["resources"]:
        story.append(_inventory_table(meta["resources"], st))
    else:
        story.append(Paragraph("No resources returned by the scan.", st["body"]))

    story.append(Paragraph("Methodology and safety", st["h2"]))
    story.append(
        Paragraph(
            "The inventory was captured by a read-only collector that runs only AWS "
            "<i>describe-*</i> calls; it never mutates or deletes a resource. The engine then "
            "applies pure detection rules (unattached disks, idle instances, unassociated "
            "Elastic IPs, idle load balancers, stale snapshots) and, for each finding, builds the "
            "exact single-resource decommission command as inert text. The engine never executes "
            "a cloud mutation - a human reviews and runs each command. Cost figures are "
            "best-effort estimates from public on-demand list prices (no Cost-and-Usage-Report).",
            st["body"],
        )
    )
    if meta["note"]:
        story.append(Spacer(1, 4))
        story.append(Paragraph(f"Snapshot note: {meta['note']}", st["small"]))

    doc.build(story)
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a FinOps waste report PDF")
    parser.add_argument("--inventory", type=Path, default=_DEFAULT_INVENTORY)
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parser.add_argument(
        "--generated-on",
        default=datetime.date.today().isoformat(),
        help="date stamp printed on the report (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--subtitle",
        default="Live AWS Account - Cost Waste Report",
        help="subtitle line under the report title",
    )
    parsed = parser.parse_args()
    written = build(parsed.inventory, parsed.out, parsed.generated_on, parsed.subtitle)
    print(f"wrote report -> {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
