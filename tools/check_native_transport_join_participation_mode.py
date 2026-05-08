#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def fail(message: str) -> None:
    raise SystemExit(message)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: check_native_transport_join_participation_mode.py <report.json>")

    report = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    markers = report.get("markers", {})

    if report.get("failure_stage") != "membership_timeout":
        fail("failure_stage must remain membership_timeout in current actual probe")
    if report.get("membership_formed") is not False:
        fail("membership_formed must remain false in current actual probe")
    if report.get("blocker_class") != "membership_timeout":
        fail("blocker_class must advance past standalone_only_bootstrap to membership_timeout")
    if markers.get("steelsearch_standalone_only") is not False:
        fail("steelsearch_standalone_only must be false after mode switch")
    if markers.get("steelsearch_native_transport_join_participation") is not True:
        fail("steelsearch_native_transport_join_participation marker missing")
    if markers.get("steelsearch_same_cluster_participation_unimplemented") is not False:
        fail("same-cluster participation must no longer be reported as unimplemented")
    if markers.get("steelsearch_bootstrap_uses_seed_peer_identity") is not True:
        fail("seed peer identity bootstrap marker missing")
    if markers.get("steelsearch_transport_handshake_accepted") is not True:
        fail("transport handshake acceptance marker missing")
    if markers.get("steelsearch_transport_follow_up_observed") is not True:
        fail("transport follow-up marker missing")

    membership_members = sorted(
        member.get("node_name")
        for member in report.get("steelsearch_membership_members", [])
        if member.get("node_name")
    )
    if membership_members != ["java-primary-1", "rust-replica-1"]:
        fail("membership members must still contain java-primary-1 and rust-replica-1")

    print(
        json.dumps(
            {
                "work_dir": report.get("work_dir"),
                "failure_stage": report.get("failure_stage"),
                "blocker_class": report.get("blocker_class"),
                "observed_node_count": report.get("observed_node_count"),
                "membership_member_names": membership_members,
                "result": (
                    "steelsearch_now_advertises_mixed_java_native_transport_join_participation_"
                    "instead_of_standalone_only_bootstrap"
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
