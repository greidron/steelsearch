#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path


SINGLETON_PATTERN = re.compile(
    r"^\[(.*?)\].*action-tagged selected channel index \[0\] type \[REG\] action \[internal:transport/handshake\].* for \[\{127\.0\.0\.1:49761\}\{"
)
RUST_CLOSE_PATTERN = re.compile(
    r"^\[(.*?)\].*closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.* with age \[(\d+)ms\]"
)
FAILED_JOIN_PATTERN = re.compile(r"^\[(.*?)\].*failed to join ")


def main():
    if len(sys.argv) != 2:
        print(
            "usage: check_publication_failure_is_downstream_of_transport_close.py <overlay-probe-report.json>",
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

    close_before_failed_join = 0
    failed_join_before_close = 0
    band_counts = {"600": {"close_before_failed_join": 0, "failed_join_before_close": 0}, "800": {"close_before_failed_join": 0, "failed_join_before_close": 0}}

    for i in range(len(singleton_rows) - 1):
        start_line = singleton_rows[i][0]
        next_line = singleton_rows[i + 1][0]
        segment = lines[start_line:next_line]

        close_ts = None
        close_age = None
        failed_join_ts = None

        for line in segment:
            close_match = RUST_CLOSE_PATTERN.search(line)
            if close_match:
                close_ts = datetime.strptime(close_match.group(1), fmt)
                close_age = int(close_match.group(3))
            join_match = FAILED_JOIN_PATTERN.search(line)
            if join_match:
                failed_join_ts = datetime.strptime(join_match.group(1), fmt)

        if close_ts is None or failed_join_ts is None or close_age is None:
            continue

        band = "600" if 600 <= close_age < 700 else "800" if 800 <= close_age < 850 else None
        if band is None:
            continue

        if close_ts <= failed_join_ts:
            close_before_failed_join += 1
            band_counts[band]["close_before_failed_join"] += 1
        else:
            failed_join_before_close += 1
            band_counts[band]["failed_join_before_close"] += 1

    result = {
        "work_dir": report.get("work_dir"),
        "close_before_failed_join": close_before_failed_join,
        "failed_join_before_close": failed_join_before_close,
        "band_counts": band_counts,
        "result": (
            "publication_failure_logging_is_mostly_downstream_of_transport_close"
            if close_before_failed_join > failed_join_before_close and close_before_failed_join >= 60
            else "publication_failure_logging_is_not_yet_shown_to_be_mostly_downstream_of_transport_close"
        ),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))

    if not result["result"].startswith("publication_failure_logging_is_mostly_downstream_of_transport_close"):
        sys.exit(1)


if __name__ == "__main__":
    main()
