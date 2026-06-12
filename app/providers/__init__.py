"""Provider registry.

Maps a provider name to its adapter. This single lookup is the only sanctioned
place provider identity is read — it dispatches to an adapter rather than letting
the core branch on a provider-name literal.
"""

from __future__ import annotations

from app.providers.aws.provider import AwsProvider
from app.providers.base import Provider

_REGISTRY: dict[str, Provider] = {
    "aws": AwsProvider(),
}


def get_provider(name: str) -> Provider:
    """Return the adapter for ``name`` (e.g. ``"aws"``)."""

    try:
        return _REGISTRY[name]
    except KeyError as exc:
        raise ValueError(f"unknown provider: {name!r}") from exc


def supported_providers() -> list[str]:
    """Return the sorted list of registered provider names."""

    return sorted(_REGISTRY)
