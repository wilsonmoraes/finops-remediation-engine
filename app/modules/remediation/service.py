"""Remediation orchestration: fetch the stored, inert command for a finding.

The command was generated deterministically at ingest time and stored. This module
only reads it back. It never executes anything — that is the architect's call.
"""

from __future__ import annotations

from app.modules.findings.service import FindingNotFoundError, get_finding
from app.modules.remediation.schemas import CommandOut


def get_command(finding_id: int) -> CommandOut:
    finding = get_finding(finding_id)
    return CommandOut(
        finding_id=finding.id,
        resource_id=finding.resource.resource_id,
        decommission_command=finding.decommission_command,
    )


__all__ = ["CommandOut", "FindingNotFoundError", "get_command"]
