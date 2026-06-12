"""Deterministic AWS decommission-command builders.

Each ``build_*`` function maps one :class:`Resource` to the exact AWS CLI command
that decommissions it — a single resource, identified by id and region. The output
is inert text: the engine persists and displays it for a human to review and run.
Nothing here executes a command, calls boto3, or touches the network.

Determinism is the contract: the same resource always yields the same string.
"""

from __future__ import annotations

from collections.abc import Callable

from app.providers.base import (
    EBS_VOLUME,
    EC2_INSTANCE,
    ELASTIC_IP,
    LOAD_BALANCER,
    SNAPSHOT,
    Resource,
    UnsupportedResourceError,
)


def build_delete_volume_cmd(resource: Resource) -> str:
    return f"aws ec2 delete-volume --volume-id {resource.resource_id} --region {resource.region}"


def build_terminate_instance_cmd(resource: Resource) -> str:
    return (
        f"aws ec2 terminate-instances --instance-ids {resource.resource_id} "
        f"--region {resource.region}"
    )


def build_release_address_cmd(resource: Resource) -> str:
    return (
        f"aws ec2 release-address --allocation-id {resource.resource_id} "
        f"--region {resource.region}"
    )


def build_delete_snapshot_cmd(resource: Resource) -> str:
    return (
        f"aws ec2 delete-snapshot --snapshot-id {resource.resource_id} "
        f"--region {resource.region}"
    )


def build_delete_load_balancer_cmd(resource: Resource) -> str:
    return (
        f"aws elbv2 delete-load-balancer --load-balancer-arn {resource.resource_id} "
        f"--region {resource.region}"
    )


_BUILDERS: dict[str, Callable[[Resource], str]] = {
    EBS_VOLUME: build_delete_volume_cmd,
    EC2_INSTANCE: build_terminate_instance_cmd,
    ELASTIC_IP: build_release_address_cmd,
    SNAPSHOT: build_delete_snapshot_cmd,
    LOAD_BALANCER: build_delete_load_balancer_cmd,
}


def build_decommission_cmd(resource: Resource) -> str:
    """Dispatch to the builder for ``resource.resource_type``."""

    builder = _BUILDERS.get(resource.resource_type)
    if builder is None:
        raise UnsupportedResourceError(
            f"no decommission command for resource_type {resource.resource_type!r}"
        )
    return builder(resource)
