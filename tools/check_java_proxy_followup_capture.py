#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_proxy_followup_capture.py <capture.json> <primary.stdout>",
            file=sys.stderr,
        )
        return 2

    capture_path = Path(sys.argv[1])
    primary_log_path = Path(sys.argv[2])

    capture = json.loads(capture_path.read_text())
    primary_log = primary_log_path.read_text()

    action_counts = {}
    for entry in capture:
        action = entry.get("action_hint")
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1

    has_tcp_handshake = action_counts.get("internal:tcp/handshake", 0) > 0
    has_transport_handshake = action_counts.get("internal:transport/handshake", 0) > 0
    has_follower_check = action_counts.get("internal:coordination/fault_detection/follower_check", 0) > 0

    followup_failed = "followup connection failed" in primary_log
    connection_reset = "connection reset" in primary_log

    if has_tcp_handshake and has_transport_handshake and followup_failed and connection_reset:
        result = "followup_reset_blocked"
    elif has_follower_check:
        result = "follower_check_reached"
    else:
        result = "insufficient_capture"

    print(
        json.dumps(
            {
                "capture_path": str(capture_path),
                "primary_log_path": str(primary_log_path),
                "action_counts": action_counts,
                "followup_failed": followup_failed,
                "connection_reset": connection_reset,
                "result": result,
            },
            indent=2,
        )
    )
    return 0 if result in {"followup_reset_blocked", "follower_check_reached"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
