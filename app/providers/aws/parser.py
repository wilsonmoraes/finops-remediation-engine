"""Parse AWS exports (inventory JSON or billing/inventory CSV) into resources.

Two input shapes are supported, both carrying the same normalized columns:

- **JSON** — a list of resource objects (an AWS inventory/Config-style export).
- **CSV** — one resource per row; tags as either a JSON ``tags`` cell or
  ``tag:<Key>`` columns (a flattened Cost-and-Usage-Report-style export).

The parser is pure: it reads bytes and returns :class:`Resource` objects. It does
not touch the database, the network, or any cloud SDK.
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.providers.base import ExportParseError, Resource

_SERVICE_BY_TYPE = {
    "ebs_volume": "ec2",
    "ec2_instance": "ec2",
    "elastic_ip": "ec2",
    "snapshot": "ec2",
    "load_balancer": "elasticloadbalancing",
}

_TRUE = {"true", "1", "yes", "attached", "in-use"}


def parse(filename: str, content: bytes) -> list[Resource]:
    """Parse ``content`` based on the extension of ``filename``."""

    lowered = filename.lower()
    if lowered.endswith(".json"):
        return _parse_json(content)
    if lowered.endswith(".csv"):
        return _parse_csv(content)
    raise ExportParseError(f"unsupported export type: {filename!r} (expected .json or .csv)")


def _parse_json(content: bytes) -> list[Resource]:
    try:
        data = json.loads(content.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ExportParseError(f"invalid JSON export: {exc}") from exc
    rows = data.get("resources", data) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise ExportParseError("JSON export must be a list of resources")
    return [_row_to_resource(row) for row in rows]


def _parse_csv(content: bytes) -> list[Resource]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ExportParseError(f"invalid CSV encoding: {exc}") from exc
    reader = csv.DictReader(io.StringIO(text))
    return [_row_to_resource(_collect_csv_tags(row)) for row in reader]


def _collect_csv_tags(row: dict[str, str]) -> dict[str, Any]:
    """Fold ``tag:<Key>`` columns into a ``tags`` dict; leave other cells as-is."""

    tags: dict[str, str] = {}
    flat: dict[str, Any] = {}
    items: list[tuple[Any, Any]] = list(row.items())
    for key, value in items:
        if key is None:
            continue
        if key.startswith("tag:"):
            tags[key[len("tag:") :]] = value
        else:
            flat[key] = value
    if "tags" in flat and isinstance(flat["tags"], str) and flat["tags"].strip():
        try:
            flat_tags = json.loads(flat["tags"])
        except json.JSONDecodeError as exc:
            raise ExportParseError(f"invalid 'tags' JSON in CSV row: {exc}") from exc
        if isinstance(flat_tags, dict):
            tags.update({str(k): str(v) for k, v in flat_tags.items()})
    flat["tags"] = tags
    return flat


def _row_to_resource(row: dict[str, Any]) -> Resource:
    resource_type = str(row.get("resource_type", "")).strip()
    if not resource_type:
        raise ExportParseError("row missing 'resource_type'")
    resource_id = str(row.get("resource_id", "")).strip()
    if not resource_id:
        raise ExportParseError("row missing 'resource_id'")

    tags_value = row.get("tags", {})
    tags = tags_value if isinstance(tags_value, dict) else {}

    return Resource(
        provider="aws",
        account_id=str(row.get("account_id", "unknown")),
        region=str(row.get("region", "us-east-1")),
        service=_SERVICE_BY_TYPE.get(resource_type, "unknown"),
        resource_type=resource_type,
        resource_id=resource_id,
        state=str(row.get("state", "")).strip().lower(),
        monthly_cost=_to_float(row.get("monthly_cost", 0)),
        attached=_to_bool(row.get("attached", False)),
        last_activity_at=_clean_optional(row.get("last_activity_at")),
        tags={str(k): str(v) for k, v in tags.items()},
        raw={k: v for k, v in row.items() if k != "tags"},
    )


def _to_float(value: Any) -> float:
    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (ValueError, TypeError) as exc:
        raise ExportParseError(f"non-numeric monthly_cost: {value!r}") from exc


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in _TRUE


def _clean_optional(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value).strip()
