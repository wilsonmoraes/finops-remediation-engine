"""The AWS adapter wiring parser + remediation into the Provider protocol."""

from __future__ import annotations

from app.providers.aws import parser, remediation
from app.providers.base import Resource


class AwsProvider:
    """Adapter implementing the :class:`~app.providers.base.Provider` protocol for AWS."""

    name = "aws"

    def parse(self, filename: str, content: bytes) -> list[Resource]:
        return parser.parse(filename, content)

    def build_decommission_cmd(self, resource: Resource) -> str:
        return remediation.build_decommission_cmd(resource)
