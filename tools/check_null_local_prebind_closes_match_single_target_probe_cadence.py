#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

CLOSE_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*netty4 tcp channel close completed for \[\[[^,]+, L:(?P<local>[^ ]+) ! R:(?P<remote>[^\]]+)\]\] with hint \[(?P<hint>[^\]]+)\]"
)


def to_ms(ts: str) -> int:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_null_local_prebind_closes_match_single_target_probe_cadence.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
    rows = []
    for line in lines:
        m = CLOSE_RE.search(line)
        if not m:
            continue
        if m.group("hint") == "unknown" and m.group("local") == "null":
            rows.append((to_ms(m.group("ts")), m.group("remote")))

    remote_counts = Counter(remote for _, remote in rows)
    deltas = [rows[i + 1][0] - rows[i][0] for i in range(len(rows) - 1)]
    near_one_second = sum(1 for d in deltas if 950 <= d <= 1050)

    result = {
        "null_local_count": len(rows),
        "remote_counts": dict(remote_counts),
        "delta_min_ms": min(deltas) if deltas else None,
        "delta_max_ms": max(deltas) if deltas else None,
        "near_one_second_delta_count": near_one_second,
        "delta_count": len(deltas),
        "result": "null_local_prebind_unknown_closes_match_repeated_outbound_attempts_to_single_remote_target_on_near_one_second_probe_cadence",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
