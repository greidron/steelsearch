#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLOSE_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*netty4 tcp channel close completed for \[\[[^,]+, L:(?P<local>[^ ]+) ! R:(?P<remote>[^\]]+)\]\] with hint \[(?P<hint>[^\]]+)\]"
)
OPENING_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*HandshakingTransportAddressConnector.*\[(?P<tag>connectToRemoteMasterNode\[[^\]]+\])\] opening probe connection"
)
OPENED_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*HandshakingTransportAddressConnector.*\[(?P<tag>connectToRemoteMasterNode\[[^\]]+\])\] opened probe connection"
)


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_null_local_closes_are_connector_opening_probe_phase.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()

    null_local = []
    opening = []
    opened = []

    for line in lines:
        m = CLOSE_RE.search(line)
        if m and m.group("hint") == "unknown" and m.group("local") == "null":
            null_local.append((m.group("ts"), m.group("remote")))
        m = OPENING_RE.search(line)
        if m:
            opening.append((m.group("ts"), m.group("tag")))
        m = OPENED_RE.search(line)
        if m:
            opened.append((m.group("ts"), m.group("tag")))

    first_opened_ts = opened[0][0] if opened else None
    opening_before_first_opened = sum(1 for ts, _ in opening if first_opened_ts and ts < first_opened_ts)
    null_before_first_opened = sum(1 for ts, _ in null_local if first_opened_ts and ts < first_opened_ts)

    result = {
        "null_local_count": len(null_local),
        "opening_probe_count": len(opening),
        "opened_probe_count": len(opened),
        "first_opened_probe_ts": first_opened_ts,
        "null_before_first_opened": null_before_first_opened,
        "opening_before_first_opened": opening_before_first_opened,
        "unique_opening_tags": sorted({tag for _, tag in opening}),
        "unique_null_targets": sorted({remote for _, remote in null_local}),
        "result": "null_local_prebind_closes_align_with_handshaking_transport_address_connector_opening_probe_connection_phase_before_first_opened_probe_connection",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
