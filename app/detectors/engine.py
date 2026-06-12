"""Run the detection rules over a set of resources and attach commands.

The engine is the pure composition layer: for each resource it runs every rule,
and for each hit it asks the provider for the deterministic decommission command.
The result is a list of :class:`Finding` objects — everything the persistence and
dashboard layers need, with no I/O performed here.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.detectors.rules import RULES, RuleConfig, RuleHit
from app.providers.base import Provider, Resource, UnsupportedResourceError


@dataclass(frozen=True, slots=True)
class Finding:
    """A detected piece of waste plus the command to remediate it."""

    resource: Resource
    rule: str
    severity: str
    monthly_waste: float
    risk_score: int
    rationale: str
    decommission_command: str


def detect(resources: list[Resource], provider: Provider, cfg: RuleConfig) -> list[Finding]:
    """Return one finding per (resource, firing rule), ordered by waste descending."""

    findings: list[Finding] = []
    for resource in resources:
        for rule in RULES:
            hit = rule(resource, cfg)
            if hit is not None:
                findings.append(_to_finding(resource, hit, provider))
    findings.sort(key=lambda f: f.monthly_waste, reverse=True)
    return findings


def _to_finding(resource: Resource, hit: RuleHit, provider: Provider) -> Finding:
    try:
        command = provider.build_decommission_cmd(resource)
    except UnsupportedResourceError:
        command = "# no decommission command available for this resource type"
    return Finding(
        resource=resource,
        rule=hit.rule,
        severity=hit.severity,
        monthly_waste=hit.monthly_waste,
        risk_score=hit.risk_score,
        rationale=hit.rationale,
        decommission_command=command,
    )
