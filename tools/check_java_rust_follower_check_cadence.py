#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path


FOLLOWER_DISCONNECTED_RE = re.compile(
    r"^\[(?P<ts>[^\]]+)\]\[INFO \]\[o\.o\.c\.c\.FollowersChecker \].* disconnected$"
)


def parse_ts(raw: str) -> datetime:
    return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S,%f")


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_rust_follower_check_cadence.py <mixed-probe-report.json> <ping-schedule-seconds>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    ping_schedule_seconds = float(sys.argv[2])
    report = json.loads(report_path.read_text())
    artifacts = report.get("artifacts") or {}
    stdout_path = Path(artifacts.get("opensearch_stdout", ""))
    capture = report.get("steelsearch_transport_capture") or []

    disconnected_timestamps = []
    if stdout_path.exists():
        for line in stdout_path.read_text(encoding="utf-8", errors="replace").splitlines():
            match = FOLLOWER_DISCONNECTED_RE.search(line)
            if match:
                disconnected_timestamps.append(parse_ts(match.group("ts")))

    intervals = []
    for prev, cur in zip(disconnected_timestamps, disconnected_timestamps[1:]):
        intervals.append((cur - prev).total_seconds())

    keepalive_count = sum(1 for entry in capture if entry.get("is_keepalive_ping"))
    publish_state_count = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint")
        == "internal:cluster/coordination/publish_state"
    )
    max_gap_seconds = max(intervals) if intervals else None
    min_gap_seconds = min(intervals) if intervals else None

    gaps_below_schedule = 0
    gaps_at_or_above_schedule = 0
    for interval in intervals:
        if interval < ping_schedule_seconds:
            gaps_below_schedule += 1
        else:
            gaps_at_or_above_schedule += 1

    if (
        keepalive_count == 0
        and publish_state_count == 0
        and max_gap_seconds is not None
        and max_gap_seconds < ping_schedule_seconds
    ):
        result = "follower_check_cadence_blocks_keepalive_idle_window"
    elif (
        keepalive_count == 0
        and publish_state_count == 0
        and gaps_below_schedule > 0
        and gaps_at_or_above_schedule > 0
    ):
        result = "logged_follower_check_gaps_cross_ping_schedule_without_keepalive"
    elif keepalive_count > 0:
        result = "keepalive_observed"
    else:
        result = "cadence_probe_inconclusive"

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "ping_schedule_seconds": ping_schedule_seconds,
                "follower_disconnected_count": len(disconnected_timestamps),
                "gaps_below_schedule": gaps_below_schedule,
                "gaps_at_or_above_schedule": gaps_at_or_above_schedule,
                "min_gap_seconds": min_gap_seconds,
                "max_gap_seconds": max_gap_seconds,
                "keepalive_count": keepalive_count,
                "publish_state_count": publish_state_count,
                "result": result,
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
