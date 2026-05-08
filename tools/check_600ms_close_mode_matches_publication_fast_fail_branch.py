#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
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


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_600ms_close_mode_matches_publication_fast_fail_branch.py <overlay-probe-report.json>",
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

    band_stats = {"600": [], "800": []}
    for i in range(len(singleton_rows) - 1):
        start_line = singleton_rows[i][0]
        next_line = singleton_rows[i + 1][0]
        segment = lines[start_line:next_line]

        publish_state_ts = None
        close_age = None
        close_ts = None
        segment_text = "\n".join(segment)
        for line in segment:
            action_match = ACTION_PATTERN.search(line)
            if action_match and "rust-replica-1" in action_match.group(5):
                if action_match.group(4) == "internal:cluster/coordination/publish_state":
                    publish_state_ts = datetime.strptime(action_match.group(1), fmt)
            close_match = RUST_CLOSE_PATTERN.search(line)
            if close_match:
                close_age = int(close_match.group(3))
                close_ts = datetime.strptime(close_match.group(1), fmt)

        if close_age is None or publish_state_ts is None or close_ts is None:
            continue

        band = "600" if 600 <= close_age < 700 else "800" if 800 <= close_age < 850 else None
        if band is None:
            continue

        band_stats[band].append(
            {
                "publish_to_close_ms": int((close_ts - publish_state_ts).total_seconds() * 1000),
                "has_failed_to_join": "failed to join" in segment_text,
                "has_publication_failed": "publication failed" in segment_text,
                "has_marking_faulty": "marking node as faulty" in segment_text,
            }
        )

    result = {
        "work_dir": report.get("work_dir"),
        "band_counts": {band: len(rows) for band, rows in band_stats.items()},
        "publish_to_close_ms": {
            band: {
                "min": min(row["publish_to_close_ms"] for row in rows),
                "median": median(row["publish_to_close_ms"] for row in rows),
                "max": max(row["publish_to_close_ms"] for row in rows),
            }
            for band, rows in band_stats.items()
        },
        "failed_to_join_counts": {
            band: sum(1 for row in rows if row["has_failed_to_join"]) for band, rows in band_stats.items()
        },
        "publication_failed_counts": {
            band: sum(1 for row in rows if row["has_publication_failed"]) for band, rows in band_stats.items()
        },
        "marking_faulty_counts": {
            band: sum(1 for row in rows if row["has_marking_faulty"]) for band, rows in band_stats.items()
        },
        "result": (
            "600ms_close_mode_matches_a_publication_fast_fail_branch_with_shorter_post_publish_dwell"
            if band_stats["600"]
            and band_stats["800"]
            and median(row["publish_to_close_ms"] for row in band_stats["600"])
            < median(row["publish_to_close_ms"] for row in band_stats["800"])
            else "600ms_close_mode_is_not_yet_separated_as_a_publication_fast_fail_branch"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith("600ms_close_mode_matches_a_publication_fast_fail_branch"):
        sys.exit(1)


if __name__ == "__main__":
    main()
