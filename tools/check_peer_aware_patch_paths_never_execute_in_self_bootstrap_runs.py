#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def capture_counts(path: str):
    captures = json.loads(Path(path).read_text())
    hints = [(row.get("first_frame") or {}).get("action_hint") for row in captures]
    return {
        "publish_state": sum(1 for hint in hints if hint == "internal:cluster/coordination/publish_state"),
        "follower_check": sum(
            1 for hint in hints if hint == "internal:coordination/fault_detection/follower_check"
        ),
        "tcp_handshake": sum(1 for hint in hints if hint == "internal:tcp/handshake"),
    }


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_peer_aware_patch_paths_never_execute_in_self_bootstrap_runs.py <main.rs> <capture-a> <capture-b>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    a = capture_counts(sys.argv[2])
    b = capture_counts(sys.argv[3])

    patch_is_limited_to_publish_and_follower = (
        "non_self_publish_seen" in source
        and 'Some("internal:cluster/coordination/publish_state")' in source
        and 'Some("internal:coordination/fault_detection/follower_check")' in source
    )

    print(f"patch_is_limited_to_publish_and_follower={patch_is_limited_to_publish_and_follower}")
    print(f"run_a={a}")
    print(f"run_b={b}")

    if (
        patch_is_limited_to_publish_and_follower
        and a["publish_state"] == 0
        and a["follower_check"] == 0
        and b["publish_state"] == 0
        and b["follower_check"] == 0
        and a["tcp_handshake"] > 0
        and b["tcp_handshake"] > 0
    ):
        print(
            "peer_aware_patch_paths_never_execute_in_self_bootstrap_runs_so_current_regression_points_back_to_upstream_discovery_nondeterminism"
        )
        return 0

    print("inconclusive_peer_aware_patch_execution")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
