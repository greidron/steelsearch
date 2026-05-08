#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_start_join_publish_are_not_reused_on_transport_handshake_channels.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())

    first_counts = collections.Counter()
    transport_handshake_post_follow_up = collections.Counter()
    transport_handshake_first = 0
    for capture in report.get("steelsearch_transport_capture") or []:
        first_action = (capture.get("first_frame") or {}).get("action_hint")
        if first_action:
            first_counts[first_action] += 1
        if first_action == "internal:transport/handshake":
            transport_handshake_first += 1
            post_action = (capture.get("post_follow_up_frame") or {}).get("action_hint")
            if post_action:
                transport_handshake_post_follow_up[post_action] += 1

    result = {
        "report_path": str(report_path),
        "transport_handshake_first_count": transport_handshake_first,
        "transport_handshake_post_follow_up_counts": dict(transport_handshake_post_follow_up),
        "fresh_first_frame_counts": {
            "internal:cluster/coordination/start_join": first_counts.get(
                "internal:cluster/coordination/start_join", 0
            ),
            "internal:cluster/coordination/publish_state": first_counts.get(
                "internal:cluster/coordination/publish_state", 0
            ),
        },
        "result": (
            "start_join_and_publish_state_open_as_fresh_sockets_because_transport_handshake_channels_do_not_reuse_into_those_actions"
            if transport_handshake_first > 0
            and not transport_handshake_post_follow_up
            and first_counts.get("internal:cluster/coordination/start_join", 0) > 0
            and first_counts.get("internal:cluster/coordination/publish_state", 0) > 0
            else "transport_handshake_reuse_gap_not_resolved"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
