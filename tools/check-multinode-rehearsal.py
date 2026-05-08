#!/usr/bin/env python3
"""Validate local multi-node Steelsearch rehearsal readiness and membership evidence."""

from __future__ import annotations

import argparse
import json
import time
import urllib.request
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest")
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--stability-window", type=float, default=3.0)
    parser.add_argument("--poll-interval", type=float, default=0.5)
    return parser.parse_args()


def fetch_cluster_view(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url.rstrip("/") + "/_steelsearch/dev/cluster", timeout=2.0) as response:
        return json.loads(response.read().decode("utf-8"))


def required_quorum(nodes: list[dict[str, Any]]) -> int:
    eligible = 0
    for node in nodes:
        roles = set((node.get("roles") or []))
        if "cluster_manager" in roles:
            eligible += 1
    if eligible == 0:
        raise SystemExit("no cluster_manager-eligible nodes found in membership evidence")
    return (eligible // 2) + 1


def validate_membership_manifest(
    manifest: dict[str, Any],
    node_entry: dict[str, Any],
    expected_cluster_uuid: str | None,
    expected_node_ids: set[str],
) -> dict[str, Any]:
    membership_path = Path(node_entry["data_path"]) / "production-membership.json"
    if not membership_path.exists():
        raise SystemExit(f"missing production membership manifest: {membership_path}")
    membership = json.loads(membership_path.read_text(encoding="utf-8"))
    if membership.get("cluster_name") != manifest.get("cluster_name"):
        raise SystemExit(
            f"membership cluster_name mismatch for {node_entry['node_id']}: "
            f"{membership.get('cluster_name')} != {manifest.get('cluster_name')}"
        )
    cluster_uuid = membership.get("cluster_uuid")
    if not cluster_uuid:
        raise SystemExit(f"membership cluster_uuid missing for {node_entry['node_id']}")
    if expected_cluster_uuid is not None and cluster_uuid != expected_cluster_uuid:
        raise SystemExit(
            f"membership cluster_uuid mismatch for {node_entry['node_id']}: "
            f"{cluster_uuid} != {expected_cluster_uuid}"
        )
    if membership.get("local_node_id") != node_entry.get("node_id"):
        raise SystemExit(
            f"membership local_node_id mismatch for {node_entry['node_id']}: "
            f"{membership.get('local_node_id')} != {node_entry.get('node_id')}"
        )
    members = membership.get("members") or {}
    member_ids = set(members.keys())
    if member_ids != expected_node_ids:
        raise SystemExit(
            f"membership member set mismatch for {node_entry['node_id']}: "
            f"{sorted(member_ids)} != {sorted(expected_node_ids)}"
        )
    return {
        "node_id": node_entry["node_id"],
        "membership_path": str(membership_path),
        "cluster_uuid": cluster_uuid,
        "member_count": len(member_ids),
        "roles": (members.get(node_entry["node_id"]) or {}).get("roles", []),
    }


def validate_manifest(
    manifest_path: Path,
    timeout: float,
    stability_window: float,
    poll_interval: float,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    expected_cluster_uuid: str | None = None
    required_stable_polls = max(1, int(stability_window / poll_interval + 0.999))
    last_signature: dict[str, Any] | None = None
    stable_polls = 0

    while time.monotonic() < deadline:
        if not manifest_path.exists():
            time.sleep(min(poll_interval, 0.25))
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        nodes = manifest.get("nodes") or []
        if not nodes:
            time.sleep(min(poll_interval, 0.25))
            continue

        cluster_views = []
        ready = True
        for node in nodes:
            try:
                payload = fetch_cluster_view(node["http_url"])
            except Exception:
                ready = False
                break
            ready = ready and payload.get("formed") is True and payload.get("number_of_nodes") == len(nodes)
            cluster_views.append(
                {
                    "node_id": node["node_id"],
                    "formed": payload.get("formed"),
                    "number_of_nodes": payload.get("number_of_nodes"),
                    "cluster_manager_node_id": payload.get("cluster_manager_node_id"),
                }
            )
        if not ready:
            stable_polls = 0
            last_signature = None
            time.sleep(poll_interval)
            continue

        expected_node_ids = {node["node_id"] for node in nodes}
        membership_files = []
        for node in nodes:
            membership_summary = validate_membership_manifest(
                manifest,
                node,
                expected_cluster_uuid,
                expected_node_ids,
            )
            membership_files.append(membership_summary)
            expected_cluster_uuid = membership_summary["cluster_uuid"]

        cluster_manager_ids = {view.get("cluster_manager_node_id") for view in cluster_views}
        if len(cluster_manager_ids) != 1:
            stable_polls = 0
            last_signature = None
            time.sleep(poll_interval)
            continue

        current_signature = {
            "cluster_uuid": expected_cluster_uuid,
            "cluster_manager_node_id": next(iter(cluster_manager_ids)),
            "node_ids": sorted(expected_node_ids),
        }
        if current_signature == last_signature:
            stable_polls += 1
        else:
            last_signature = current_signature
            stable_polls = 1

        if stable_polls < required_stable_polls:
            time.sleep(poll_interval)
            continue

        return {
            "ready": True,
            "cluster_name": manifest.get("cluster_name"),
            "cluster_uuid": expected_cluster_uuid,
            "node_count": len(nodes),
            "required_quorum": required_quorum(membership_files),
            "stability_window": stability_window,
            "poll_interval": poll_interval,
            "stable_polls": stable_polls,
            "cluster_manager_node_id": current_signature["cluster_manager_node_id"],
            "cluster_views": cluster_views,
            "membership_files": membership_files,
        }

    raise SystemExit("multi-node Steelsearch cluster did not become ready")


def main() -> int:
    args = parse_args()
    result = validate_manifest(
        Path(args.manifest),
        args.timeout,
        args.stability_window,
        args.poll_interval,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
