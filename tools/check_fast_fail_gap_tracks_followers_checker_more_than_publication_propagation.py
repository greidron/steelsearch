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
RUST_CLOSE_PATTERN = re.compile(
    r"^\[(.*?)\].*closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.* with age \[(\d+)ms\]"
)
FOLLOWERS_DISCONNECTED_PATTERN = re.compile(r"^\[(.*?)\].*FollowersChecker.* disconnected")
FOLLOWERS_MARKING_PATTERN = re.compile(r"^\[(.*?)\].*FollowersChecker.* marking node as faulty")
FAILED_JOIN_PATTERN = re.compile(r"^\[(.*?)\].*failed to join ")


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_fast_fail_gap_tracks_followers_checker_more_than_publication_propagation.py <overlay-probe-report.json>",
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

        close_ts = None
        close_age = None
        disconnected_ts = None
        marking_ts = None
        failed_join_ts = None

        for line in segment:
            close_match = RUST_CLOSE_PATTERN.search(line)
            if close_match:
                close_ts = datetime.strptime(close_match.group(1), fmt)
                close_age = int(close_match.group(3))
            disc_match = FOLLOWERS_DISCONNECTED_PATTERN.search(line)
            if disc_match:
                disconnected_ts = datetime.strptime(disc_match.group(1), fmt)
            mark_match = FOLLOWERS_MARKING_PATTERN.search(line)
            if mark_match:
                marking_ts = datetime.strptime(mark_match.group(1), fmt)
            join_match = FAILED_JOIN_PATTERN.search(line)
            if join_match:
                failed_join_ts = datetime.strptime(join_match.group(1), fmt)

        if close_ts is None or close_age is None:
            continue
        band = "600" if 600 <= close_age < 700 else "800" if 800 <= close_age < 850 else None
        if band is None:
            continue

        band_rows[band].append(
            {
                "disc_to_close_ms": int((close_ts - disconnected_ts).total_seconds() * 1000) if disconnected_ts else None,
                "mark_to_close_ms": int((close_ts - marking_ts).total_seconds() * 1000) if marking_ts else None,
                "failjoin_to_close_ms": int((close_ts - failed_join_ts).total_seconds() * 1000) if failed_join_ts else None,
            }
        )

    result = {
        "work_dir": report.get("work_dir"),
        "band_counts": {band: len(rows) for band, rows in band_rows.items()},
        "disc_to_close_ms": {
            band: {
                "min": min(row["disc_to_close_ms"] for row in rows if row["disc_to_close_ms"] is not None),
                "median": median(row["disc_to_close_ms"] for row in rows if row["disc_to_close_ms"] is not None),
                "max": max(row["disc_to_close_ms"] for row in rows if row["disc_to_close_ms"] is not None),
            }
            for band, rows in band_rows.items()
        },
        "mark_to_close_ms": {
            band: {
                "min": min(row["mark_to_close_ms"] for row in rows if row["mark_to_close_ms"] is not None),
                "median": median(row["mark_to_close_ms"] for row in rows if row["mark_to_close_ms"] is not None),
                "max": max(row["mark_to_close_ms"] for row in rows if row["mark_to_close_ms"] is not None),
            }
            for band, rows in band_rows.items()
            if any(row["mark_to_close_ms"] is not None for row in rows)
        },
        "failjoin_to_close_ms": {
            band: {
                "min": min(row["failjoin_to_close_ms"] for row in rows if row["failjoin_to_close_ms"] is not None),
                "median": median(row["failjoin_to_close_ms"] for row in rows if row["failjoin_to_close_ms"] is not None),
                "max": max(row["failjoin_to_close_ms"] for row in rows if row["failjoin_to_close_ms"] is not None),
            }
            for band, rows in band_rows.items()
        },
        "result": (
            "fast_fail_gap_tracks_followers_checker_fault_escalation_more_than_publication_failure_propagation"
            if median(row["disc_to_close_ms"] for row in band_rows["600"] if row["disc_to_close_ms"] is not None)
            < median(row["disc_to_close_ms"] for row in band_rows["800"] if row["disc_to_close_ms"] is not None)
            and abs(median(row["disc_to_close_ms"] for row in band_rows["600"] if row["disc_to_close_ms"] is not None)) <= 5
            else "fast_fail_gap_is_not_yet_more_tightly_linked_to_followers_checker_fault_escalation"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "fast_fail_gap_tracks_followers_checker_fault_escalation_more_than_publication_failure_propagation"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
