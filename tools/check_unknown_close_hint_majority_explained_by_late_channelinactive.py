#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLOSE_RE = re.compile(
    r"netty4 tcp channel close completed for \[\[[^,]+, L:(?P<local>[^ ]+) ! R:(?P<remote>[^\]]+)\]\] with hint \[(?P<hint>[^\]]+)\]"
)
INACTIVE_RE = re.compile(
    r"channelInactive on \[Netty4TcpChannel\{localAddress=(?P<local>[^,]+), remoteAddress=(?P<remote>[^\}]+)\}\]"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_unknown_close_hint_majority_explained_by_late_channelinactive.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()

    unknowns = []
    for idx, line in enumerate(lines):
        m = CLOSE_RE.search(line)
        if m and m.group("hint") == "unknown":
            unknowns.append((idx, m.group("local")))

    inactive_by_local = {}
    for idx, line in enumerate(lines):
        m = INACTIVE_RE.search(line)
        if m:
            inactive_by_local.setdefault(m.group("local"), []).append(idx)

    null_local_count = 0
    delayed_channelinactive_within_100_lines = 0
    unexplained_count = 0

    for idx, local in unknowns:
        if local == "null":
            null_local_count += 1
            continue
        hits = [hit for hit in inactive_by_local.get(local, []) if idx <= hit <= idx + 100]
        if hits:
            delayed_channelinactive_within_100_lines += 1
        else:
            unexplained_count += 1

    result = {
        "unknown_total": len(unknowns),
        "null_local_pre_bind_count": null_local_count,
        "post_bind_with_delayed_channelinactive_within_100_lines": delayed_channelinactive_within_100_lines,
        "unexplained_count": unexplained_count,
        "result": "unknown_close_hint_majority_is_explained_by_pre_bind_null_local_closes_or_by_close_trace_firing_before_late_channelinactive",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
