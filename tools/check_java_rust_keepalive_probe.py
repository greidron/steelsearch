#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_keepalive_probe.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    keepalive_count = sum(1 for entry in capture if entry.get("is_keepalive_ping"))
    follower_check_count = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint")
        == "internal:coordination/fault_detection/follower_check"
    )
    publish_state_count = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint")
        == "internal:cluster/coordination/publish_state"
    )

    stdout_log = report.get("opensearch_stdout_log")
    if not stdout_log:
        stdout_log = ((report.get("artifacts") or {}).get("opensearch_stdout"))
    follower_disconnected = False
    if stdout_log:
        log_path = Path(stdout_log)
        if log_path.exists():
            follower_disconnected = "FollowerChecker" in log_path.read_text()

    if keepalive_count == 0 and follower_disconnected and follower_check_count > 0:
        result = "keepalive_not_observed_and_follower_still_disconnected"
    elif keepalive_count > 0 and follower_disconnected:
        result = "keepalive_observed_but_follower_still_disconnected"
    elif keepalive_count > 0 and not follower_disconnected:
        result = "keepalive_observed_and_follower_disconnect_cleared"
    else:
        result = "keepalive_not_observed_and_follower_disconnect_not_seen"

    payload = {
        "report_path": str(report_path),
        "keepalive_count": keepalive_count,
        "follower_check_count": follower_check_count,
        "publish_state_count": publish_state_count,
        "follower_disconnected": follower_disconnected,
        "blocker_class": report.get("blocker_class"),
        "result": result,
    }
    print(json.dumps(payload, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
