"""Read-only collector: snapshot a live AWS account into the engine's export schema.

This is an OPTIONAL helper, separate from the engine. It runs only read-only
``aws ... describe-*`` calls through the AWS CLI and writes a normalized inventory
JSON that ``POST /ingest`` accepts. It never mutates anything and never deletes a
resource — that stays a human decision on the generated commands.

Cost columns are best-effort estimates (no Cost-and-Usage-Report is read), using
public on-demand list prices for the resource's region-agnostic defaults. Treat
them as ballpark waste, not an invoice.

Usage:
    python scripts/collect_aws_inventory.py                 # all enabled regions
    python scripts/collect_aws_inventory.py --regions us-east-1 us-west-2
    python scripts/collect_aws_inventory.py --out data/aws_live_inventory.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_OUT = _REPO_ROOT / "data" / "aws_live_inventory.json"

_EBS_GB_MONTH = {
    "gp3": 0.08,
    "gp2": 0.10,
    "io1": 0.125,
    "io2": 0.125,
    "st1": 0.045,
    "sc1": 0.015,
    "standard": 0.05,
}
_SNAPSHOT_GB_MONTH = 0.05
_EIP_MONTH = 3.60
_LB_MONTH = 18.0


class AwsCliError(RuntimeError):
    """Raised when an aws CLI call fails."""


def _aws(args: list[str]) -> Any:
    """Run a read-only aws CLI command and return parsed JSON."""

    proc = subprocess.run(
        ["aws", *args, "--output", "json"],
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise AwsCliError(proc.stderr.strip() or f"aws {' '.join(args)} failed")
    if not proc.stdout.strip():
        return {}
    return json.loads(proc.stdout)


def _enabled_regions() -> list[str]:
    data = _aws(
        [
            "ec2",
            "describe-regions",
            "--filters",
            "Name=opt-in-status,Values=opt-in-not-required,opted-in",
        ]
    )
    return sorted(r["RegionName"] for r in data.get("Regions", []))


def _tags(raw: list[dict[str, str]] | None) -> dict[str, str]:
    return {t["Key"]: t.get("Value", "") for t in (raw or [])}


def _volume_cost(volume: dict[str, Any]) -> float:
    size = float(volume.get("Size", 0))
    price = _EBS_GB_MONTH.get(str(volume.get("VolumeType", "gp3")), 0.08)
    return round(size * price, 2)


def _collect_region(region: str, account: str) -> list[dict[str, Any]]:
    resources: list[dict[str, Any]] = []
    volume_cost_by_id: dict[str, float] = {}

    volumes = _aws(["ec2", "describe-volumes", "--region", region]).get("Volumes", [])
    for vol in volumes:
        cost = _volume_cost(vol)
        volume_cost_by_id[vol["VolumeId"]] = cost
        resources.append(
            {
                "resource_type": "ebs_volume",
                "resource_id": vol["VolumeId"],
                "region": region,
                "account_id": account,
                "state": vol.get("State", ""),
                "attached": bool(vol.get("Attachments")),
                "monthly_cost": cost,
                "last_activity_at": str(vol.get("CreateTime", ""))[:10] or None,
                "tags": _tags(vol.get("Tags")),
            }
        )

    instances = _aws(["ec2", "describe-instances", "--region", region])
    for reservation in instances.get("Reservations", []):
        for inst in reservation.get("Instances", []):
            state = inst.get("State", {}).get("Name", "")
            attached_vols = [
                bdm["Ebs"]["VolumeId"]
                for bdm in inst.get("BlockDeviceMappings", [])
                if bdm.get("Ebs", {}).get("VolumeId")
            ]
            cost = round(sum(volume_cost_by_id.get(v, 0.0) for v in attached_vols), 2)
            resources.append(
                {
                    "resource_type": "ec2_instance",
                    "resource_id": inst["InstanceId"],
                    "region": region,
                    "account_id": account,
                    "state": state,
                    "attached": state == "running",
                    "monthly_cost": cost,
                    "last_activity_at": None,
                    "tags": _tags(inst.get("Tags")),
                }
            )

    addresses = _aws(["ec2", "describe-addresses", "--region", region]).get("Addresses", [])
    for addr in addresses:
        associated = bool(addr.get("AssociationId"))
        resources.append(
            {
                "resource_type": "elastic_ip",
                "resource_id": addr.get("AllocationId", addr.get("PublicIp", "")),
                "region": region,
                "account_id": account,
                "state": "associated" if associated else "unassociated",
                "attached": associated,
                "monthly_cost": _EIP_MONTH,
                "last_activity_at": None,
                "tags": _tags(addr.get("Tags")),
            }
        )

    snapshots = _aws(["ec2", "describe-snapshots", "--owner-ids", "self", "--region", region]).get(
        "Snapshots", []
    )
    for snap in snapshots:
        resources.append(
            {
                "resource_type": "snapshot",
                "resource_id": snap["SnapshotId"],
                "region": region,
                "account_id": account,
                "state": snap.get("State", ""),
                "attached": False,
                "monthly_cost": round(float(snap.get("VolumeSize", 0)) * _SNAPSHOT_GB_MONTH, 2),
                "last_activity_at": str(snap.get("StartTime", ""))[:10] or None,
                "tags": _tags(snap.get("Tags")),
            }
        )

    resources.extend(_collect_load_balancers(region, account))
    return resources


def _collect_load_balancers(region: str, account: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    lbs = _aws(["elbv2", "describe-load-balancers", "--region", region]).get("LoadBalancers", [])
    for lb in lbs:
        arn = lb["LoadBalancerArn"]
        has_healthy = _load_balancer_has_targets(arn, region)
        out.append(
            {
                "resource_type": "load_balancer",
                "resource_id": arn,
                "region": region,
                "account_id": account,
                "state": lb.get("State", {}).get("Code", ""),
                "attached": has_healthy,
                "monthly_cost": _LB_MONTH,
                "last_activity_at": str(lb.get("CreatedTime", ""))[:10] or None,
                "tags": {"Name": lb.get("LoadBalancerName", "")},
            }
        )
    return out


def _load_balancer_has_targets(lb_arn: str, region: str) -> bool:
    groups = _aws(
        ["elbv2", "describe-target-groups", "--load-balancer-arn", lb_arn, "--region", region]
    ).get("TargetGroups", [])
    for group in groups:
        health = _aws(
            [
                "elbv2",
                "describe-target-health",
                "--target-group-arn",
                group["TargetGroupArn"],
                "--region",
                region,
            ]
        ).get("TargetHealthDescriptions", [])
        if health:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only AWS inventory collector")
    parser.add_argument("--regions", nargs="*", help="regions to scan (default: all enabled)")
    parser.add_argument("--out", type=Path, default=_DEFAULT_OUT)
    parsed = parser.parse_args()

    identity = _aws(["sts", "get-caller-identity"])
    account = str(identity.get("Account", "unknown"))
    print(f"account: {account}")

    regions = parsed.regions or _enabled_regions()
    print(f"scanning {len(regions)} region(s): {', '.join(regions)}")

    resources: list[dict[str, Any]] = []
    for region in regions:
        try:
            found = _collect_region(region, account)
        except AwsCliError as exc:
            print(f"  {region}: skipped ({exc})", file=sys.stderr)
            continue
        print(f"  {region}: {len(found)} resource(s)")
        resources.extend(found)

    parsed.out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "_note": "estimated monthly costs (no CUR); read-only describe-* snapshot",
        "resources": resources,
    }
    parsed.out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(f"wrote {len(resources)} resource(s) -> {parsed.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
