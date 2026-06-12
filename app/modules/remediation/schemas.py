"""Response models for the remediation module."""

from __future__ import annotations

from pydantic import BaseModel


class CommandOut(BaseModel):
    """The decommission command for one finding.

    ``executed`` is always ``False`` and ``execute_hint`` documents that the engine
    never runs the command — a human reviews and runs it.
    """

    finding_id: int
    resource_id: str
    decommission_command: str
    executed: bool = False
    execute_hint: str = "Review, then run this command yourself in an authenticated shell."
