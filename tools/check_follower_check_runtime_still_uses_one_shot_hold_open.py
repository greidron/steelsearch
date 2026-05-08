#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_follower_check_runtime_still_uses_one_shot_hold_open.py <transport-seed-capture.json> <main.rs>",
            file=sys.stderr,
        )
        return 2

    captures = json.loads(Path(sys.argv[1]).read_text())
    source = Path(sys.argv[2]).read_text()

    follower_rows = [
        row
        for row in captures
        if (row.get("first_frame") or {}).get("action_hint")
        == "internal:coordination/fault_detection/follower_check"
    ]
    publish_rows = [
        row
        for row in captures
        if (row.get("first_frame") or {}).get("action_hint")
        == "internal:cluster/coordination/publish_state"
    ]

    follower_remote_eof = sum(1 for row in follower_rows if row.get("connection_end") == "remote_eof")
    follower_keepalive = sum(1 for row in follower_rows if (row.get("proactive_keepalive_count") or 0) > 0)
    publish_keepalive = sum(1 for row in publish_rows if (row.get("proactive_keepalive_count") or 0) > 0)

    follower_false = bool(
        re.search(
            r'internal:coordination/fault_detection/follower_check".*?hold_transport_channel_open\(\s*&mut stream,\s*transport_identity,\s*&mut post_follow_up_frame,\s*&mut post_follow_up_frame_received_at_ms,\s*false,',
            source,
            re.S,
        )
    )
    publish_true = bool(
        re.search(
            r'internal:cluster/coordination/publish_state".*?hold_transport_channel_open\(\s*&mut stream,\s*transport_identity,\s*&mut post_follow_up_frame,\s*&mut post_follow_up_frame_received_at_ms,\s*true,',
            source,
            re.S,
        )
    )
    start_join_true = bool(
        re.search(
            r'internal:cluster/coordination/start_join".*?hold_transport_channel_open\(\s*&mut stream,\s*transport_identity,\s*&mut post_follow_up_frame,\s*&mut post_follow_up_frame_received_at_ms,\s*true,',
            source,
            re.S,
        )
    )

    print(f"follower_check_count={len(follower_rows)}")
    print(f"follower_check_remote_eof={follower_remote_eof}")
    print(f"follower_check_proactive_keepalive={follower_keepalive}")
    print(f"publish_state_count={len(publish_rows)}")
    print(f"publish_state_proactive_keepalive={publish_keepalive}")
    print(f"source_follower_check_hold_open_false={follower_false}")
    print(f"source_publish_state_hold_open_true={publish_true}")
    print(f"source_start_join_hold_open_true={start_join_true}")

    if (
        follower_rows
        and follower_remote_eof == len(follower_rows)
        and follower_keepalive == 0
        and follower_false
        and publish_true
        and start_join_true
    ):
        print(
            "follower_check_runtime_still_uses_one_shot_hold_open_while_publish_state_and_start_join_use_reusable_path"
        )
        return 0

    print("inconclusive_follower_check_hold_open_split")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
