#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_followerschecker_disconnect_matches_remote_eof_after_response.py <transport-seed-capture.json> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    captures = json.loads(Path(sys.argv[1]).read_text())
    lines = Path(sys.argv[2]).read_text().splitlines()

    follower_rows = []
    for row in captures:
        first_frame = row.get("first_frame") or {}
        if first_frame.get("action_hint") == "internal:coordination/fault_detection/follower_check":
            follower_rows.append(row)

    follower_response_then_remote_eof = sum(
        1
        for row in follower_rows
        if row.get("response_frame") is not None and row.get("connection_end") == "remote_eof"
    )

    java_follower_disconnected = sum(
        1
        for line in lines
        if "FollowersChecker" in line and "rust-replica-1" in line and " disconnected" in line
    )
    java_follower_faulty = sum(
        1
        for line in lines
        if "FollowersChecker" in line and "rust-replica-1" in line and "marking node as faulty" in line
    )
    java_transport_failure = sum(
        1
        for line in lines
        if "steelsearch_publication_response_class=transport_failure" in line and "rust-replica-1" in line
    )

    print(f"rust_follower_check_count={len(follower_rows)}")
    print(f"rust_follower_response_then_remote_eof={follower_response_then_remote_eof}")
    print(f"java_follower_disconnected={java_follower_disconnected}")
    print(f"java_follower_faulty={java_follower_faulty}")
    print(f"java_transport_failure={java_transport_failure}")

    if (
        follower_rows
        and follower_response_then_remote_eof == len(follower_rows)
        and java_follower_disconnected == len(follower_rows)
        and java_follower_faulty == len(follower_rows)
        and java_transport_failure >= 1
    ):
        print(
            "followerschecker_disconnect_matches_rust_response_then_remote_eof_one_shot_lifecycle_not_missing_response"
        )
        return 0

    print("inconclusive_followerschecker_disconnect_vs_remote_eof")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
