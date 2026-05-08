#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def summarize_capture(path: str):
    captures = json.loads(Path(path).read_text())
    follower = 0
    publish = 0
    for row in captures:
        hint = (row.get("first_frame") or {}).get("action_hint")
        if hint == "internal:coordination/fault_detection/follower_check":
            follower += 1
        if hint == "internal:cluster/coordination/publish_state":
            publish += 1
    return follower, publish


def summarize_stdout(path: str):
    lines = Path(path).read_text().splitlines()
    rust_publish = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={rust-replica-1}" in line
    )
    one_node = sum(1 for line in lines if "elected-as-cluster-manager ([1] nodes joined)" in line)
    node_left = sum(1 for line in lines if "node-left[{rust-replica-1}" in line)
    return rust_publish, one_node, node_left


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_follower_check_flip_ab_points_to_discovery_nondeterminism.py <capture-a> <stdout-a> <capture-b> <stdout-b>",
            file=sys.stderr,
        )
        return 2

    a_follower, a_publish = summarize_capture(sys.argv[1])
    a_rust_publish, a_one_node, a_node_left = summarize_stdout(sys.argv[2])
    b_follower, b_publish = summarize_capture(sys.argv[3])
    b_rust_publish, b_one_node, b_node_left = summarize_stdout(sys.argv[4])

    print(f"run_a_follower_check_count={a_follower}")
    print(f"run_a_publish_state_count={a_publish}")
    print(f"run_a_rust_publish_accepted={a_rust_publish}")
    print(f"run_a_one_node_election={a_one_node}")
    print(f"run_a_node_left={a_node_left}")
    print(f"run_b_follower_check_count={b_follower}")
    print(f"run_b_publish_state_count={b_publish}")
    print(f"run_b_rust_publish_accepted={b_rust_publish}")
    print(f"run_b_one_node_election={b_one_node}")
    print(f"run_b_node_left={b_node_left}")

    if (
        a_follower > 0
        and a_publish > 0
        and a_rust_publish > 0
        and a_node_left > 0
        and b_follower == 0
        and b_publish == 0
        and b_rust_publish == 0
        and b_one_node > 0
    ):
        print(
            "follower_check_flip_ab_points_to_run_to_run_discovery_nondeterminism_more_than_single_deterministic_pre_bootstrap_gate"
        )
        return 0

    print("inconclusive_follower_check_flip_ab")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
