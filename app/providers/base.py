"""Provider-neutral domain shapes and the adapter protocol.

The core of the engine never speaks AWS or Azure vocabulary directly. Each
provider's parser maps its native export onto the normalized :class:`Resource`
shape below, and the detectors and dashboard reason only about that shape. A
provider also knows how to turn one of its resources into a decommission command
string — the :class:`Provider` protocol ties the two together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

EBS_VOLUME = "ebs_volume"
EC2_INSTANCE = "ec2_instance"
ELASTIC_IP = "elastic_ip"
LOAD_BALANCER = "load_balancer"
SNAPSHOT = "snapshot"


@dataclass(frozen=True, slots=True)
class Resource:
    """A single cloud resource, normalized across providers.

    Native states and types are mapped onto provider-agnostic values
    (``resource_type`` is one of the module constants above; ``state`` is a
    lowercase native-ish status). Detection rules key on these fields, never on
    ``provider``.
    """

    provider: str
    account_id: str
    region: str
    service: str
    resource_type: str
    resource_id: str
    state: str
    monthly_cost: float
    attached: bool
    last_activity_at: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    raw: dict[str, object] = field(default_factory=dict)


@runtime_checkable
class Provider(Protocol):
    """The adapter every cloud provider implements."""

    name: str

    def parse(self, filename: str, content: bytes) -> list[Resource]:
        """Parse a raw export (by extension) into normalized resources."""
        ...

    def build_decommission_cmd(self, resource: Resource) -> str:
        """Return the exact, single-resource CLI command to decommission ``resource``."""
        ...


class UnsupportedResourceError(ValueError):
    """Raised when no decommission command is defined for a resource type."""


class ExportParseError(ValueError):
    """Raised when an export file cannot be parsed into resources."""
