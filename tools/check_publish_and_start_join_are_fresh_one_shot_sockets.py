#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


TARGETS = {
    "internal:cluster/coordination/start_join",
    "internal:cluster/coordination/publish_state",
}


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_publish_and_start_join_are_fresh_one_shot_sockets.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())

    shape_counts = collections.Counter()
    for capture in report.get("steelsearch_transport_capture") or []:
        action = (capture.get("first_frame") or {}).get("action_hint")
        if action not in TARGETS:
            continue
        shape_counts[
            (
                action,
                capture.get("follow_up_frame") is None,
                capture.get("post_follow_up_frame") is None,
                capture.get("connection_end"),
            )
        ] += 1

    result = {
        "report_path": str(report_path),
        "shape_counts": {
            f"{action}|follow_up_none={follow_up_none}|post_follow_up_none={post_follow_up_none}|connection_end={connection_end}": count
            for (action, follow_up_none, post_follow_up_none, connection_end), count in shape_counts.items()
        },
        "result": (
            "start_join_and_publish_state_are_fresh_first_frame_only_one_shot_sockets"
            if shape_counts
            and all(
                follow_up_none and post_follow_up_none and connection_end == "remote_eof"
                for (_, follow_up_none, post_follow_up_none, connection_end) in shape_counts
            )
            else "start_join_and_publish_state_do_not_share_a_single_fresh_one_shot_socket_shape"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if shape_counts else 1


if __name__ == "__main__":
    raise SystemExit(main())
