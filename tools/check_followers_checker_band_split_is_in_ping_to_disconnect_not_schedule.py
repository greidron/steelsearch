#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from statistics import median


SINGLETON_PATTERN = re.compile(
    r"^\[(.*?)\].*action-tagged selected channel index \[0\] type \[REG\] action \[internal:transport/handshake\].* for \[\{127\.0\.0\.1:49761\}\{"
)
ACTION_PATTERN = re.compile(
    r"^\[(.*?)\].*action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\].* for \[(.*)\]$"
)
RUST_CLOSE_PATTERN = re.compile(
    r"^\[(.*?)\].*closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.* with age \[(\d+)ms\]"
)
FOLLOWERS_DISCONNECTED_PATTERN = re.compile(r"^\[(.*?)\].*FollowersChecker.* disconnected")


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_followers_checker_band_split_is_in_ping_to_disconnect_not_schedule.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    lines = Path(report["artifacts"]["opensearch_stdout"]).read_text(errors="replace").splitlines()
    fmt = "%Y-%m-%dT%H:%M:%S,%f"

    singleton_rows = []
    for i, line in enumerate(lines):
        match = SINGLETON_PATTERN.search(line)
        if match:
            singleton_rows.append((i, datetime.strptime(match.group(1), fmt)))

    band_rows = {"600": [], "800": []}
    for i in range(len(singleton_rows) - 1):
        start_line = singleton_rows[i][0]
        next_line = singleton_rows[i + 1][0]
        segment = lines[start_line:next_line]

        close_age = None
        publish_ts = None
        ping_ts = None
        disconnected_ts = None

        for line in segment:
            action_match = ACTION_PATTERN.search(line)
            if action_match and "rust-replica-1" in action_match.group(5):
                ts = datetime.strptime(action_match.group(1), fmt)
                action = action_match.group(4)
                if action == "internal:cluster/coordination/publish_state":
                    publish_ts = ts
                elif action == "internal:coordination/fault_detection/follower_check":
                    ping_ts = ts
            close_match = RUST_CLOSE_PATTERN.search(line)
            if close_match:
                close_age = int(close_match.group(3))
            disconnected_match = FOLLOWERS_DISCONNECTED_PATTERN.search(line)
            if disconnected_match:
                disconnected_ts = datetime.strptime(disconnected_match.group(1), fmt)

        if close_age is None or publish_ts is None or ping_ts is None or disconnected_ts is None:
            continue
        band = "600" if 600 <= close_age < 700 else "800" if 800 <= close_age < 850 else None
        if band is None:
            continue

        band_rows[band].append(
            {
                "publish_to_ping_ms": int((ping_ts - publish_ts).total_seconds() * 1000),
                "ping_to_disconnected_ms": int((disconnected_ts - ping_ts).total_seconds() * 1000),
            }
        )

    result = {
        "work_dir": report.get("work_dir"),
        "band_counts": {band: len(rows) for band, rows in band_rows.items()},
        "publish_to_ping_ms": {
            band: {
                "min": min(row["publish_to_ping_ms"] for row in rows),
                "median": median(row["publish_to_ping_ms"] for row in rows),
                "max": max(row["publish_to_ping_ms"] for row in rows),
            }
            for band, rows in band_rows.items()
        },
        "ping_to_disconnected_ms": {
            band: {
                "min": min(row["ping_to_disconnected_ms"] for row in rows),
                "median": median(row["ping_to_disconnected_ms"] for row in rows),
                "max": max(row["ping_to_disconnected_ms"] for row in rows),
            }
            for band, rows in band_rows.items()
        },
        "result": (
            "followers_checker_band_split_is_in_ping_to_disconnect_path_not_in_publish_to_ping_schedule"
            if abs(median(row["publish_to_ping_ms"] for row in band_rows["600"]) - median(row["publish_to_ping_ms"] for row in band_rows["800"])) <= 15
            and median(row["ping_to_disconnected_ms"] for row in band_rows["800"])
            - median(row["ping_to_disconnected_ms"] for row in band_rows["600"])
            >= 100
            else "followers_checker_band_split_is_not_yet_localized_to_ping_to_disconnect_path"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "followers_checker_band_split_is_in_ping_to_disconnect_path_not_in_publish_to_ping_schedule"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
