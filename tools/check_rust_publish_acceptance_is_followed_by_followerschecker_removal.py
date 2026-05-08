#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_rust_publish_acceptance_is_followed_by_followerschecker_removal.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text().splitlines()
    rust_accept = []
    follower_disconnected = []
    follower_faulty = []
    node_left = []
    transport_failure = []

    for idx, line in enumerate(lines, start=1):
        if re.search(
            r"steelsearch_handlePublishResponse_gate=accepted .*sourceNode=\{rust-replica-1\}",
            line,
        ):
            rust_accept.append(idx)
        if "FollowersChecker" in line and "rust-replica-1" in line and " disconnected" in line:
            follower_disconnected.append(idx)
        if "FollowersChecker" in line and "rust-replica-1" in line and "marking node as faulty" in line:
            follower_faulty.append(idx)
        if "node-left[{rust-replica-1}" in line:
            node_left.append(idx)
        if "steelsearch_publication_response_class=transport_failure" in line and "rust-replica-1" in line:
            transport_failure.append(idx)

    accepted_then_disconnect = sum(
        1 for a in rust_accept if any(d > a for d in follower_disconnected)
    )
    disconnect_then_node_left = sum(
        1 for d in follower_disconnected if any(n > d for n in node_left)
    )
    disconnect_then_transport_failure = sum(
        1 for d in follower_disconnected if any(t > d for t in transport_failure)
    )

    print(f"rust_accept={len(rust_accept)}")
    print(f"follower_disconnected={len(follower_disconnected)}")
    print(f"follower_faulty={len(follower_faulty)}")
    print(f"node_left={len(node_left)}")
    print(f"transport_failure={len(transport_failure)}")
    print(f"accepted_then_disconnect={accepted_then_disconnect}")
    print(f"disconnect_then_node_left={disconnect_then_node_left}")
    print(f"disconnect_then_transport_failure={disconnect_then_transport_failure}")

    if (
        rust_accept
        and follower_disconnected
        and follower_faulty
        and node_left
        and transport_failure
        and accepted_then_disconnect == len(rust_accept)
        and disconnect_then_node_left >= 1
        and disconnect_then_transport_failure >= 1
    ):
        print(
            "rust_publish_acceptance_is_followed_by_followerschecker_disconnect_and_node_left_removal_before_persistent_membership"
        )
        return 0

    print("inconclusive_rust_publish_acceptance_followerschecker_path")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
