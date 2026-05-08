#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_rust_ping_channel_idle_window.py <mixed-probe-report.json> <ping-idle-window-ms>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    idle_window_ms = int(sys.argv[2])
    report = json.loads(report_path.read_text())
    capture = report.get("steelsearch_transport_capture") or []

    follower_windows = []
    keepalive_count = 0
    for entry in capture:
        if entry.get("is_keepalive_ping"):
            keepalive_count += 1
            continue
        action = (entry.get("first_frame") or {}).get("action_hint")
        if action != "internal:coordination/fault_detection/follower_check":
            continue
        response_at = entry.get("response_frame_sent_at_ms")
        end_at = entry.get("connection_end_at_ms")
        if response_at is None or end_at is None:
            continue
        follower_windows.append(end_at - response_at)

    min_window_ms = min(follower_windows) if follower_windows else None
    max_window_ms = max(follower_windows) if follower_windows else None

    if follower_windows and max_window_ms < idle_window_ms:
        result = "follower_check_channel_closes_before_ping_idle_window"
    elif follower_windows and max_window_ms >= idle_window_ms and keepalive_count == 0:
        result = "idle_window_elapsed_without_observed_keepalive"
    else:
        result = "idle_window_probe_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "idle_window_ms": idle_window_ms,
                "follower_check_window_count": len(follower_windows),
                "min_window_ms": min_window_ms,
                "max_window_ms": max_window_ms,
                "keepalive_count": keepalive_count,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
