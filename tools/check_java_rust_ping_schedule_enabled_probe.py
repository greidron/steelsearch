#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_ping_schedule_enabled_probe.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    artifacts = report.get("artifacts") or {}
    stderr_path = Path(artifacts.get("opensearch_stderr", ""))
    stdout_path = Path(artifacts.get("opensearch_stdout", ""))
    capture = report.get("steelsearch_transport_capture") or []

    stderr_text = stderr_path.read_text(encoding="utf-8", errors="replace") if stderr_path.exists() else ""
    stdout_text = stdout_path.read_text(encoding="utf-8", errors="replace") if stdout_path.exists() else ""

    ping_schedule_enabled = "OpenSearch transport ping_schedule: 1s" in stderr_text
    keepalive_count = sum(1 for entry in capture if entry.get("is_keepalive_ping"))
    publish_state_count = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint")
        == "internal:cluster/coordination/publish_state"
    )
    follower_check_count = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint")
        == "internal:coordination/fault_detection/follower_check"
    )
    follower_disconnected = "FollowerChecker" in stdout_text

    if ping_schedule_enabled and keepalive_count == 0 and publish_state_count == 0 and follower_disconnected:
        result = "ping_schedule_enabled_but_no_keepalive_or_publish_state_progress"
    elif ping_schedule_enabled and keepalive_count > 0 and follower_disconnected:
        result = "ping_schedule_enabled_keepalive_observed_but_follower_still_disconnected"
    elif ping_schedule_enabled and keepalive_count > 0 and publish_state_count > 0:
        result = "ping_schedule_enabled_and_publication_progress_observed"
    else:
        result = "ping_schedule_enabled_probe_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "ping_schedule_enabled": ping_schedule_enabled,
                "keepalive_count": keepalive_count,
                "publish_state_count": publish_state_count,
                "follower_check_count": follower_check_count,
                "follower_disconnected": follower_disconnected,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
