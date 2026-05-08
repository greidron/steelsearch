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


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_singleton_reprobe_outliers_match_close_to_next_wakeup_phase.py <overlay-probe-report.json>",
            file=sys.stderr,
        )
        sys.exit(2)

    report = json.loads(Path(sys.argv[1]).read_text())
    stdout_lines = Path(report["artifacts"]["opensearch_stdout"]).read_text(errors="replace").splitlines()
    fmt = "%Y-%m-%dT%H:%M:%S,%f"

    singleton_rows = []
    for i, line in enumerate(stdout_lines):
        match = SINGLETON_PATTERN.search(line)
        if match:
            singleton_rows.append((i, datetime.strptime(match.group(1), fmt)))

    cycles = []
    for i in range(len(singleton_rows) - 1):
        start_line, start_ts = singleton_rows[i]
        next_line, next_ts = singleton_rows[i + 1]
        segment = stdout_lines[start_line:next_line]
        rust_close_entries = []
        for line in segment:
            match = RUST_CLOSE_PATTERN.search(line)
            if match:
                rust_close_entries.append(
                    {
                        "ts": datetime.strptime(match.group(1), fmt),
                        "age_ms": int(match.group(3)),
                    }
                )
        if not rust_close_entries:
            continue
        last_close = rust_close_entries[-1]
        cycles.append(
            {
                "interval_ms": int((next_ts - start_ts).total_seconds() * 1000),
                "close_age_ms": last_close["age_ms"],
                "close_to_next_probe_ms": int((next_ts - last_close["ts"]).total_seconds() * 1000),
            }
        )

    close_to_next = [cycle["close_to_next_probe_ms"] for cycle in cycles]
    shortest = min(cycles, key=lambda c: c["interval_ms"])
    longest = max(cycles, key=lambda c: c["interval_ms"])

    result = {
        "work_dir": report.get("work_dir"),
        "cycle_count": len(cycles),
        "close_to_next_probe_gap_ms": {
            "min": min(close_to_next),
            "median": median(close_to_next),
            "max": max(close_to_next),
        },
        "shortest_interval_case": shortest,
        "longest_interval_case": longest,
        "result": (
            "singleton_reprobe_outliers_are_better_explained_by_close_to_next_wakeup_phase_difference_than_by_scheduler_jitter_alone"
            if shortest["close_to_next_probe_ms"] <= 100
            and longest["close_to_next_probe_ms"] >= 700
            else "singleton_reprobe_outliers_are_not_yet_explained_by_close_to_next_wakeup_phase_difference"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith(
        "singleton_reprobe_outliers_are_better_explained_by_close_to_next_wakeup_phase_difference"
    ):
        sys.exit(1)


if __name__ == "__main__":
    main()
