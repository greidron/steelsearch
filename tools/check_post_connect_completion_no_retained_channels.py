#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_post_connect_completion_no_retained_channels.py <stdout.log> <report.json>"
        )

    stdout = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    report = load_json(sys.argv[2])

    completed_full_connection_count = stdout.count("completed full connection with [")
    capture = report.get("steelsearch_transport_capture") or []

    action_counts = {}
    first_frame_only_counts = {}
    for action in [
        "internal:discovery/request_peers",
        "internal:coordination/fault_detection/follower_check",
        "internal:cluster/coordination/publish_state",
    ]:
        entries = [e for e in capture if (e.get("first_frame") or {}).get("action_hint") == action]
        action_counts[action] = len(entries)
        first_frame_only_counts[action] = sum(1 for e in entries if e.get("follow_up_frame") is None)

    all_first_frame_only = all(
        action_counts[action] > 0 and first_frame_only_counts[action] == action_counts[action]
        for action in action_counts
    )

    result = (
        "connect_to_node_completion_occurs_but_later_coordinator_actions_still_arrive_only_on_fresh_first_frame_sockets_so_default_multi_channel_retention_never_sticks"
        if completed_full_connection_count > 0 and all_first_frame_only
        else "post_connect_completion_no_retained_channels_not_fully_established"
    )

    print(json.dumps({
        "completed_full_connection_count": completed_full_connection_count,
        "action_counts": action_counts,
        "first_frame_only_counts": first_frame_only_counts,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
