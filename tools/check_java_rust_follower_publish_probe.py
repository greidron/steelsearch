#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_follower_publish_probe.py <report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))

    stdout_path = Path(report["artifacts"]["opensearch_stdout"])
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace")

    action_counts = {}
    for entry in report.get("steelsearch_transport_capture") or []:
        for key in ("first_frame", "follow_up_frame", "post_follow_up_frame"):
            frame = entry.get(key)
            if not frame:
                continue
            action = frame.get("action_hint")
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1

    follower_disconnected = "FollowerChecker" in stdout_text and "disconnected" in stdout_text
    publish_state_observed = (
        action_counts.get("internal:cluster/coordination/publish_state", 0) > 0
    )

    if not follower_disconnected and publish_state_observed:
        result = "publish_state_only_blocker"
    elif follower_disconnected and not publish_state_observed:
        result = "follower_disconnected_before_publish_state"
    elif follower_disconnected and publish_state_observed:
        result = "follower_disconnected_with_publish_state"
    else:
        result = "insufficient_signal"

    output = {
        "report_path": str(report_path),
        "opensearch_stdout_path": str(stdout_path),
        "action_counts": action_counts,
        "follower_disconnected": follower_disconnected,
        "publish_state_observed": publish_state_observed,
        "result": result,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
