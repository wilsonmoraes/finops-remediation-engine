"""End-to-end API tests via FastAPI TestClient against a temp SQLite database."""

from __future__ import annotations

from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_ingest_summary_findings_flow(client: TestClient, inventory_bytes: bytes) -> None:
    resp = client.post(
        "/ingest",
        files={"file": ("aws_inventory.json", inventory_bytes, "application/json")},
    )
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["resource_count"] == 9
    assert summary["finding_count"] >= 5
    assert summary["total_monthly_waste"] > 0

    s = client.get("/summary").json()
    assert s["monthly_waste"] > 0
    assert s["annual_waste"] == round(s["monthly_waste"] * 12, 2)
    assert 0 < s["risk_score"] <= 100
    assert "high" in s["by_severity"]

    findings = client.get("/findings").json()
    assert len(findings) == summary["finding_count"]
    wastes = [f["monthly_waste"] for f in findings]
    assert wastes == sorted(wastes, reverse=True)

    first_id = findings[0]["id"]
    one = client.get(f"/findings/{first_id}").json()
    assert one["decommission_command"].startswith("aws ")

    cmd = client.get(f"/findings/{first_id}/command.txt")
    assert cmd.status_code == 200
    assert cmd.text.startswith("aws ")


def _ingest_sample(client: TestClient, inventory_bytes: bytes) -> None:
    client.post(
        "/ingest",
        files={"file": ("aws_inventory.json", inventory_bytes, "application/json")},
    )


def test_findings_filter_by_severity(client: TestClient, inventory_bytes: bytes) -> None:
    _ingest_sample(client, inventory_bytes)
    high = client.get("/findings", params={"severity": "high"}).json()
    assert high
    assert all(f["severity"] == "high" for f in high)


def test_ingest_rejects_unsupported_extension(client: TestClient) -> None:
    resp = client.post("/ingest", files={"file": ("export.txt", b"nope", "text/plain")})
    assert resp.status_code == 400


def test_missing_finding_returns_404(client: TestClient) -> None:
    assert client.get("/findings/99999").status_code == 404
    assert client.get("/findings/99999/command").status_code == 404


def test_dashboard_renders(client: TestClient, inventory_bytes: bytes) -> None:
    _ingest_sample(client, inventory_bytes)
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Monthly waste" in resp.text
    assert "aws ec2" in resp.text
