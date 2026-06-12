"""Pure orphan/idle detection rules.

Each rule is a function ``(Resource, RuleConfig) -> RuleHit | None``. A rule keys
only on the normalized resource shape (never on the provider name) and returns a
:class:`RuleHit` describing the waste when the resource looks orphaned or idle,
or ``None`` otherwise.

These functions are pure and deterministic: the "as of" date used for age checks
is passed in via :class:`RuleConfig`, never read from the clock here, so tests are
reproducible.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.providers.base import (
    EBS_VOLUME,
    EC2_INSTANCE,
    ELASTIC_IP,
    LOAD_BALANCER,
    SNAPSHOT,
    Resource,
)

_SEVERITY_BASE = {"high": 60, "medium": 40, "low": 20}


@dataclass(frozen=True, slots=True)
class RuleConfig:
    """Thresholds and reference date for the detection rules."""

    as_of: date
    idle_vm_days: int = 14
    stale_snapshot_days: int = 90


@dataclass(frozen=True, slots=True)
class RuleHit:
    """A rule's verdict that a resource is wasteful."""

    rule: str
    severity: str
    monthly_waste: float
    risk_score: int
    rationale: str


def _risk_score(severity: str, monthly_waste: float) -> int:
    base = _SEVERITY_BASE.get(severity, 20)
    return min(100, base + min(40, round(monthly_waste)))


def _days_since(last_activity_at: str | None, as_of: date) -> int | None:
    if not last_activity_at:
        return None
    try:
        seen = date.fromisoformat(last_activity_at[:10])
    except ValueError:
        return None
    return (as_of - seen).days


def unattached_ebs_volume(resource: Resource, _cfg: RuleConfig) -> RuleHit | None:
    """Flag an EBS volume that is not attached to any instance."""

    if resource.resource_type != EBS_VOLUME or resource.attached or resource.state == "in-use":
        return None
    rationale = (
        f"EBS volume {resource.resource_id} is unattached (state={resource.state}); "
        f"it accrues storage cost with no instance using it."
    )
    return RuleHit(
        "unattached_ebs_volume",
        "high",
        resource.monthly_cost,
        _risk_score("high", resource.monthly_cost),
        rationale,
    )


def idle_ec2_instance(resource: Resource, cfg: RuleConfig) -> RuleHit | None:
    """Flag a stopped instance, or a running instance idle past the threshold."""

    if resource.resource_type != EC2_INSTANCE:
        return None
    if resource.state == "stopped":
        rationale = (
            f"EC2 instance {resource.resource_id} is stopped but still provisioned; "
            f"attached storage and addresses keep billing."
        )
        return RuleHit(
            "idle_ec2_instance",
            "high",
            resource.monthly_cost,
            _risk_score("high", resource.monthly_cost),
            rationale,
        )
    if resource.state == "running":
        idle_days = _days_since(resource.last_activity_at, cfg.as_of)
        if idle_days is not None and idle_days >= cfg.idle_vm_days:
            rationale = (
                f"EC2 instance {resource.resource_id} has been running with no activity for "
                f"{idle_days} days (threshold {cfg.idle_vm_days})."
            )
            return RuleHit(
                "idle_ec2_instance",
                "high",
                resource.monthly_cost,
                _risk_score("high", resource.monthly_cost),
                rationale,
            )
    return None


def unassociated_elastic_ip(resource: Resource, _cfg: RuleConfig) -> RuleHit | None:
    """Flag an Elastic IP not associated with a running resource."""

    if resource.resource_type != ELASTIC_IP or resource.attached:
        return None
    rationale = (
        f"Elastic IP {resource.resource_id} is unassociated; AWS bills idle public IPv4 "
        f"addresses by the hour."
    )
    return RuleHit(
        "unassociated_elastic_ip",
        "medium",
        resource.monthly_cost,
        _risk_score("medium", resource.monthly_cost),
        rationale,
    )


def idle_load_balancer(resource: Resource, _cfg: RuleConfig) -> RuleHit | None:
    """Flag a load balancer with no healthy targets."""

    if resource.resource_type != LOAD_BALANCER or resource.attached:
        return None
    rationale = (
        f"Load balancer {resource.resource_id} has no registered targets; it bills hourly "
        f"while serving nothing."
    )
    return RuleHit(
        "idle_load_balancer",
        "medium",
        resource.monthly_cost,
        _risk_score("medium", resource.monthly_cost),
        rationale,
    )


def stale_snapshot(resource: Resource, cfg: RuleConfig) -> RuleHit | None:
    """Flag an unattached snapshot older than the staleness threshold."""

    if resource.resource_type != SNAPSHOT or resource.attached:
        return None
    age_days = _days_since(resource.last_activity_at, cfg.as_of)
    if age_days is None or age_days < cfg.stale_snapshot_days:
        return None
    rationale = (
        f"Snapshot {resource.resource_id} is {age_days} days old and referenced by nothing "
        f"(threshold {cfg.stale_snapshot_days})."
    )
    return RuleHit(
        "stale_snapshot",
        "low",
        resource.monthly_cost,
        _risk_score("low", resource.monthly_cost),
        rationale,
    )


RULES = (
    unattached_ebs_volume,
    idle_ec2_instance,
    unassociated_elastic_ip,
    idle_load_balancer,
    stale_snapshot,
)
