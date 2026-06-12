"""Tests for the pure detection rules and the engine composition."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from app.detectors import rules
from app.detectors.engine import detect
from app.detectors.rules import RuleConfig
from app.providers.aws import parser
from app.providers.aws.provider import AwsProvider
from app.providers.base import Resource

_SAMPLES = Path(__file__).resolve().parent.parent / "samples"
_AS_OF = date(2026, 6, 12)
_CFG = RuleConfig(as_of=_AS_OF, idle_vm_days=14, stale_snapshot_days=90)


def _res(**overrides: object) -> Resource:
    base: dict[str, object] = {
        "provider": "aws",
        "account_id": "123456789012",
        "region": "us-east-1",
        "service": "ec2",
        "resource_type": "ebs_volume",
        "resource_id": "vol-x",
        "state": "available",
        "monthly_cost": 5.0,
        "attached": False,
    }
    base.update(overrides)
    return Resource(**base)  # type: ignore[arg-type]


def test_unattached_volume_fires_and_attached_is_silent() -> None:
    assert rules.unattached_ebs_volume(_res(), _CFG) is not None
    assert rules.unattached_ebs_volume(_res(attached=True, state="in-use"), _CFG) is None


def test_stopped_instance_fires() -> None:
    hit = rules.idle_ec2_instance(_res(resource_type="ec2_instance", state="stopped"), _CFG)
    assert hit is not None
    assert hit.severity == "high"


def test_running_instance_idle_past_threshold_fires() -> None:
    idle = _res(resource_type="ec2_instance", state="running", last_activity_at="2026-01-01")
    active = _res(resource_type="ec2_instance", state="running", last_activity_at="2026-06-11")
    assert rules.idle_ec2_instance(idle, _CFG) is not None
    assert rules.idle_ec2_instance(active, _CFG) is None


def test_unassociated_eip_fires() -> None:
    eip = _res(resource_type="elastic_ip", state="unassociated", attached=False)
    attached_eip = _res(resource_type="elastic_ip", attached=True)
    assert rules.unassociated_elastic_ip(eip, _CFG) is not None
    assert rules.unassociated_elastic_ip(attached_eip, _CFG) is None


def test_idle_load_balancer_fires() -> None:
    lb = _res(resource_type="load_balancer", attached=False)
    assert rules.idle_load_balancer(lb, _CFG) is not None


def test_stale_snapshot_respects_age_threshold() -> None:
    stale = _res(resource_type="snapshot", last_activity_at="2025-01-01")
    fresh = _res(resource_type="snapshot", last_activity_at="2026-06-10")
    assert rules.stale_snapshot(stale, _CFG) is not None
    assert rules.stale_snapshot(fresh, _CFG) is None


def test_engine_over_sample_finds_expected_waste() -> None:
    resources = parser.parse("aws_inventory.json", (_SAMPLES / "aws_inventory.json").read_bytes())
    findings = detect(resources, AwsProvider(), _CFG)

    flagged_ids = {f.resource.resource_id for f in findings}
    assert "vol-0a1unattached" in flagged_ids
    assert "i-0c3stopped" in flagged_ids
    assert "i-0d4idlerunning" in flagged_ids
    assert "eipalloc-0f6loose" in flagged_ids
    lb_cmd = next(f.decommission_command for f in findings if "dead-alb" in f.resource.resource_id)
    assert "dead-alb" in lb_cmd
    assert "snap-0g7stale" in flagged_ids

    assert "vol-0b2inuse" not in flagged_ids
    assert "i-0e5active" not in flagged_ids
    assert "snap-0h8recent" not in flagged_ids

    assert findings == sorted(findings, key=lambda f: f.monthly_waste, reverse=True)
    assert all(f.decommission_command.startswith("aws ") for f in findings)
