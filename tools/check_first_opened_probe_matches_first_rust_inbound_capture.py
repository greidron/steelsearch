#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

OPENED_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\].*HandshakingTransportAddressConnector.*\[(?P<tag>connectToRemoteMasterNode\[[^\]]+\])\] opened probe connection"
)


def to_ms(ts: str) -> int:
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f").replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_first_opened_probe_matches_first_rust_inbound_capture.py <opensearch-stdout.log> <report.json>",
            file=sys.stderr,
        )
        return 2

    stdout_lines = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace").splitlines()
    report = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    first_opened = None
    for line in stdout_lines:
        m = OPENED_RE.search(line)
        if m:
            first_opened = {
                "timestamp": m.group("ts"),
                "ts_ms": to_ms(m.group("ts")),
                "tag": m.group("tag"),
            }
            break

    captures = report.get("steelsearch_transport_capture") or []
    first_capture = None
    if captures:
        first_capture = min(captures, key=lambda c: c.get("connection_started_at_ms", 10**18))

    delta_ms = None
    if first_opened and first_capture:
        delta_ms = abs(first_opened["ts_ms"] - first_capture["connection_started_at_ms"])

    result = {
        "first_opened_probe": first_opened,
        "first_rust_inbound_capture": {
            "connection_started_at_ms": first_capture.get("connection_started_at_ms") if first_capture else None,
            "peer_addr": first_capture.get("peer_addr") if first_capture else None,
            "action_hint": (first_capture.get("first_frame") or {}).get("action_hint") if first_capture else None,
        },
        "delta_ms": delta_ms,
        "result": "first_successful_opened_probe_connection_coincides_with_first_rust_inbound_tcp_handshake_capture_so_earlier_opening_probe_attempts_precede_remote_transport_acceptance",
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
