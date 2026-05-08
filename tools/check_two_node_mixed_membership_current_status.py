#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_two_node_mixed_membership_current_status.py <report.json>")

    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    if report.get("failure_stage") != "membership_timeout":
        fail("failure_stage must be membership_timeout")
    if report.get("membership_formed") is not False:
        fail("membership_formed must be false for current status")
    observed_node_count = report.get("observed_node_count")
    if not isinstance(observed_node_count, int) or observed_node_count >= 2:
        fail("observed_node_count must remain below 2 in current actual probe")
    if report.get("blocker_class") != "standalone_only_bootstrap":
        fail("blocker_class must be standalone_only_bootstrap")

    markers = report.get("markers", {})
    if markers.get("steelsearch_standalone_only") is not True:
        fail("steelsearch_standalone_only marker missing")
    if markers.get("steelsearch_bootstrap_uses_seed_peer_identity") is not True:
        fail("steelsearch_bootstrap_uses_seed_peer_identity marker missing")
    if markers.get("steelsearch_membership_state_persisted") is not True:
        fail("steelsearch_membership_state_persisted marker missing")
    if markers.get("steelsearch_transport_accepting_connections") is not True:
        fail("steelsearch_transport_accepting_connections marker missing")
    if markers.get("steelsearch_transport_handshake_accepted") is not True:
        fail("steelsearch_transport_handshake_accepted marker missing")

    membership_members = report.get("steelsearch_membership_members", [])
    member_names = sorted(
        member.get("node_name")
        for member in membership_members
        if member.get("node_name")
    )
    if member_names != ["java-primary-1", "rust-replica-1"]:
        fail("steelsearch_membership_members must include java-primary-1 and rust-replica-1")

    bootstrap_remote_nodes = report.get("steelsearch_bootstrap_remote_nodes", [])
    remote_node_names = sorted(
        node.get("node_name")
        for node in bootstrap_remote_nodes
        if node.get("node_name")
    )
    if remote_node_names != ["java-primary-1"]:
        fail("steelsearch_bootstrap_remote_nodes must show java-primary-1")

    print(
        json.dumps(
            {
                "work_dir": report.get("work_dir"),
                "failure_stage": report.get("failure_stage"),
                "blocker_class": report.get("blocker_class"),
                "observed_node_count": observed_node_count,
                "membership_member_names": member_names,
                "result": (
                    "two_node_mixed_cluster_membership_is_not_yet_formed_in_actual_probe_and_"
                    "currently_stops_at_standalone_only_bootstrap"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
