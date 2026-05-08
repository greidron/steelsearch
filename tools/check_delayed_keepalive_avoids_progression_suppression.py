#!/usr/bin/env python3
import collections
import json
import sys
from pathlib import Path


def summarize(path: Path) -> tuple[dict[str, int], int]:
    report = json.loads(path.read_text())
    counts = collections.Counter()
    keepalive_sent = 0
    for capture in report.get("steelsearch_transport_capture") or []:
        action = (capture.get("first_frame") or {}).get("action_hint")
        if action:
            counts[action] += 1
        if capture.get("proactive_keepalive_sent_at_ms") is not None:
            keepalive_sent += 1
    return (
        {
            "request_pre_vote": counts.get("internal:cluster/request_pre_vote", 0),
            "start_join": counts.get("internal:cluster/coordination/start_join", 0),
            "publish_state": counts.get("internal:cluster/coordination/publish_state", 0),
        },
        keepalive_sent,
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_delayed_keepalive_avoids_progression_suppression.py <immediate.json> <delayed.json>",
            file=sys.stderr,
        )
        return 2

    immediate_path = Path(sys.argv[1])
    delayed_path = Path(sys.argv[2])
    immediate_counts, immediate_keepalive_sent = summarize(immediate_path)
    delayed_counts, delayed_keepalive_sent = summarize(delayed_path)

    result = {
        "immediate_report_path": str(immediate_path),
        "delayed_report_path": str(delayed_path),
        "immediate_counts": immediate_counts,
        "delayed_counts": delayed_counts,
        "immediate_keepalive_sent_count": immediate_keepalive_sent,
        "delayed_keepalive_sent_count": delayed_keepalive_sent,
        "result": (
            "delayed_keepalive_avoids_same_tick_progression_suppression"
            if immediate_counts["start_join"] == 0
            and delayed_counts["start_join"] > 0
            and delayed_counts["publish_state"] > 0
            and delayed_keepalive_sent == 0
            else "delayed_keepalive_does_not_clearly_avoid_progression_suppression"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
