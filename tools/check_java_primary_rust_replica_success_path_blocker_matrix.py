#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


TARGETS = (
    "internal:cluster/request_pre_vote",
    "internal:cluster/coordination/start_join",
    "internal:cluster/coordination/publish_state",
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_primary_rust_replica_success_path_blocker_matrix.py <membership_probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    captures = report.get("steelsearch_transport_capture") or []

    action_counts = collections.Counter()
    remote_eof_counts = collections.Counter()
    handled_follow_up_counts = collections.Counter()

    for capture in captures:
        first_action = (capture.get("first_frame") or {}).get("action_hint")
        if first_action not in TARGETS:
            continue
        action_counts[first_action] += 1
        event = capture.get("first_post_response_event")
        if event == "remote_eof":
            remote_eof_counts[first_action] += 1
        if event == "handled_follow_up_request":
            handled_follow_up_counts[first_action] += 1

    result = {
        "report_path": str(report_path),
        "action_counts": dict(action_counts),
        "remote_eof_counts": dict(remote_eof_counts),
        "handled_follow_up_counts": dict(handled_follow_up_counts),
        "result": (
            "success_path_blocker_matrix_is_pre_vote_start_join_publish_state_first_frame_only_remote_eof"
            if action_counts
            and sum(remote_eof_counts.values()) == sum(action_counts.values())
            and sum(handled_follow_up_counts.values()) == 0
            else "success_path_blocker_matrix_differs_from_pre_vote_start_join_publish_state_first_frame_only_remote_eof"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if action_counts else 1


if __name__ == "__main__":
    raise SystemExit(main())
