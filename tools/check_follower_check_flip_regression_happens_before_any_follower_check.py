#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_follower_check_flip_regression_happens_before_any_follower_check.py <transport-seed-capture.json> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    captures = json.loads(Path(sys.argv[1]).read_text())
    lines = Path(sys.argv[2]).read_text().splitlines()

    follower_check_count = sum(
        1
        for row in captures
        if (row.get("first_frame") or {}).get("action_hint")
        == "internal:coordination/fault_detection/follower_check"
    )
    publish_state_self_only = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={java-primary-1}" in line
    )
    publish_state_rust = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={rust-replica-1}" in line
    )
    one_node_election = sum(
        1
        for line in lines
        if "elected-as-cluster-manager ([1] nodes joined)" in line
    )

    print(f"follower_check_count={follower_check_count}")
    print(f"publish_state_self_only={publish_state_self_only}")
    print(f"publish_state_rust={publish_state_rust}")
    print(f"one_node_election={one_node_election}")

    if (
        follower_check_count == 0
        and publish_state_self_only > 0
        and publish_state_rust == 0
        and one_node_election > 0
    ):
        print(
            "follower_check_flip_regression_happens_before_any_follower_check_and_points_to_pre_bootstrap_gating_or_discovery_nondeterminism"
        )
        return 0

    print("inconclusive_follower_check_flip_regression_timing")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
