#!/usr/bin/env python3
import sys
from pathlib import Path


def summarize(path: str):
    lines = Path(path).read_text().splitlines()
    one_node = sum(1 for line in lines if "elected-as-cluster-manager ([1] nodes joined)" in line)
    rust_accept = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={rust-replica-1}" in line
    )
    self_accept = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={java-primary-1}" in line
    )
    return one_node, rust_accept, self_accept


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_peer_aware_gate_patch_still_self_bootstraps.py <stdout-a> <stdout-b>",
            file=sys.stderr,
        )
        return 2

    a_one, a_rust, a_self = summarize(sys.argv[1])
    b_one, b_rust, b_self = summarize(sys.argv[2])

    print(f"run_a_one_node_election={a_one}")
    print(f"run_a_rust_accept={a_rust}")
    print(f"run_a_self_accept={a_self}")
    print(f"run_b_one_node_election={b_one}")
    print(f"run_b_rust_accept={b_rust}")
    print(f"run_b_self_accept={b_self}")

    if a_one > 0 and b_one > 0 and a_rust == 0 and b_rust == 0 and a_self > 0 and b_self > 0:
        print(
            "peer_aware_gate_patch_still_self_bootstraps_in_repeated_runs_and_does_not_restore_rust_join"
        )
        return 0

    print("inconclusive_peer_aware_gate_patch")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
