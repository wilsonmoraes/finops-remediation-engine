"""Tests for the AWS export parsers (JSON + CSV)."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.providers.aws import parser
from app.providers.base import ExportParseError

_SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def test_parse_json_inventory_normalizes_fields() -> None:
    content = (_SAMPLES / "aws_inventory.json").read_bytes()
    resources = parser.parse("aws_inventory.json", content)

    assert len(resources) == 9
    vol = next(r for r in resources if r.resource_id == "vol-0a1unattached")
    assert vol.provider == "aws"
    assert vol.resource_type == "ebs_volume"
    assert vol.service == "ec2"
    assert vol.attached is False
    assert vol.monthly_cost == 8.0
    assert vol.tags["Env"] == "staging"


def test_parse_csv_folds_tag_columns() -> None:
    content = (_SAMPLES / "aws_billing.csv").read_bytes()
    resources = parser.parse("aws_billing.csv", content)

    assert len(resources) == 3
    disk = next(r for r in resources if r.resource_id == "vol-csv01orphan")
    assert disk.region == "us-west-2"
    assert disk.monthly_cost == 12.5
    assert disk.attached is False
    assert disk.tags == {"Name": "orphan-disk", "Env": "dev"}


def test_parse_rejects_unknown_extension() -> None:
    with pytest.raises(ExportParseError):
        parser.parse("export.txt", b"whatever")


def test_parse_rejects_row_without_resource_id() -> None:
    with pytest.raises(ExportParseError):
        parser.parse("x.json", b'[{"resource_type": "ebs_volume"}]')


def test_parse_csv_rejects_malformed_tags_json() -> None:
    csv_bytes = b"resource_type,resource_id,tags\n" b'ebs_volume,vol-1,"{not valid json}"\n'
    with pytest.raises(ExportParseError):
        parser.parse("x.csv", csv_bytes)


def test_parse_rejects_non_numeric_cost() -> None:
    with pytest.raises(ExportParseError):
        parser.parse(
            "x.json",
            b'[{"resource_type": "ebs_volume", "resource_id": "vol-1", "monthly_cost": "free"}]',
        )


def test_parse_json_accepts_bare_list() -> None:
    resources = parser.parse(
        "x.json",
        b'[{"resource_type": "snapshot", "resource_id": "snap-1", "region": "eu-west-1"}]',
    )
    assert resources[0].region == "eu-west-1"
    assert resources[0].monthly_cost == 0.0
