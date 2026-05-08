#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_version_only_gate_would_enable_too_early.py <main.rs> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    lines = Path(sys.argv[2]).read_text().splitlines()

    state_has_only_term_version = (
        "struct DevTransportCoordinationState" in source
        and "last_accepted_term: i64" in source
        and "last_accepted_version: i64" in source
        and "rust_join_seen" not in source
        and "non_self_publish_seen" not in source
    )

    self_accepts = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={java-primary-1}" in line
    )
    rust_accepts = sum(
        1
        for line in lines
        if "steelsearch_handlePublishResponse_gate=accepted" in line
        and "sourceNode={rust-replica-1}" in line
    )
    one_node = sum(1 for line in lines if "elected-as-cluster-manager ([1] nodes joined)" in line)

    print(f"state_has_only_term_version={state_has_only_term_version}")
    print(f"self_accepts={self_accepts}")
    print(f"rust_accepts={rust_accepts}")
    print(f"one_node_election={one_node}")

    if state_has_only_term_version and self_accepts > 0 and rust_accepts == 0 and one_node > 0:
        print(
            "version_only_gate_would_enable_too_early_in_self_only_bootstrap_and_points_to_need_for_peer_aware_post_rust_join_gate"
        )
        return 0

    print("inconclusive_version_only_gate")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
