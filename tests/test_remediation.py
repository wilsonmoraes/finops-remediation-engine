"""Tests for the deterministic AWS decommission-command builders."""

from __future__ import annotations

import pytest

from app.providers.aws import remediation
from app.providers.base import Resource, UnsupportedResourceError


def _resource(resource_type: str, resource_id: str, region: str = "us-east-1") -> Resource:
    return Resource(
        provider="aws",
        account_id="123456789012",
        region=region,
        service="ec2",
        resource_type=resource_type,
        resource_id=resource_id,
        state="available",
        monthly_cost=1.0,
        attached=False,
    )


def test_build_delete_volume_cmd() -> None:
    cmd = remediation.build_decommission_cmd(_resource("ebs_volume", "vol-1"))
    assert cmd == "aws ec2 delete-volume --volume-id vol-1 --region us-east-1"


def test_build_terminate_instance_cmd() -> None:
    cmd = remediation.build_decommission_cmd(_resource("ec2_instance", "i-1", "eu-west-1"))
    assert cmd == "aws ec2 terminate-instances --instance-ids i-1 --region eu-west-1"


def test_build_release_address_cmd() -> None:
    cmd = remediation.build_decommission_cmd(_resource("elastic_ip", "eipalloc-1"))
    assert cmd == "aws ec2 release-address --allocation-id eipalloc-1 --region us-east-1"


def test_build_delete_snapshot_cmd() -> None:
    cmd = remediation.build_decommission_cmd(_resource("snapshot", "snap-1"))
    assert cmd == "aws ec2 delete-snapshot --snapshot-id snap-1 --region us-east-1"


def test_build_delete_load_balancer_cmd() -> None:
    cmd = remediation.build_decommission_cmd(_resource("load_balancer", "arn:lb/x"))
    assert cmd == "aws elbv2 delete-load-balancer --load-balancer-arn arn:lb/x --region us-east-1"


def test_unknown_type_raises() -> None:
    with pytest.raises(UnsupportedResourceError):
        remediation.build_decommission_cmd(_resource("s3_bucket", "my-bucket"))


def test_builder_is_deterministic() -> None:
    res = _resource("ebs_volume", "vol-9")
    assert remediation.build_decommission_cmd(res) == remediation.build_decommission_cmd(res)
