#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


EVENT_RE = re.compile(
    r"Peer\{transportAddress=(?P<addr>[^,]+), discoveryNode=(?P<node>.+?), peersRequestInFlight=(?P<inflight>[^}]+)\} (?P<event>requesting peers|attempting connection|connection failed)"
)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_single_peer_connected_then_fresh_failure_reentry.py <peerfinder.java> <stdout.log>"
        )

    source = Path(sys.argv[1]).read_text()
    lines = Path(sys.argv[2]).read_text().splitlines()

    events = []
    for idx, line in enumerate(lines):
        m = EVENT_RE.search(line)
        if not m:
            continue
        if m.group("addr") != "127.0.0.1:57743":
            continue
        events.append(
            {
                "line_index": idx,
                "node": m.group("node"),
                "event": m.group("event"),
            }
        )

    connected_requesting = [
        e for e in events if e["event"] == "requesting peers" and e["node"] != "null"
    ]
    fresh_null_attempts = [
        e for e in events if e["event"] == "attempting connection" and e["node"] == "null"
    ]
    fresh_null_failures = [
        e for e in events if e["event"] == "connection failed" and e["node"] == "null"
    ]

    connected_then_later_fresh_failure = False
    if connected_requesting and fresh_null_failures:
        last_connected_line = min(e["line_index"] for e in connected_requesting)
        connected_then_later_fresh_failure = any(
            e["line_index"] > last_connected_line for e in fresh_null_failures
        )

    source_has_connected_path = "discoveryNode.set(remoteNode);" in source and "requestPeers();" in source
    source_has_fresh_failure_path = 'logger.debug(() -> new ParameterizedMessage("{} connection failed", Peer.this), e);' in source

    result = (
        "single_peer_valid_handshake_response_can_still_fall_back_to_fresh_null_discovery_failure_loop_after_connected_requesting_peers_state"
        if source_has_connected_path
        and source_has_fresh_failure_path
        and connected_requesting
        and fresh_null_attempts
        and fresh_null_failures
        and connected_then_later_fresh_failure
        else "single_peer_connected_then_fresh_failure_reentry_not_fully_established"
    )

    print(
        json.dumps(
            {
                "source_has_connected_requesting_peers_path": source_has_connected_path,
                "source_has_connection_failed_path": source_has_fresh_failure_path,
                "connected_requesting_peers_count": len(connected_requesting),
                "fresh_null_attempting_connection_count": len(fresh_null_attempts),
                "fresh_null_connection_failed_count": len(fresh_null_failures),
                "connected_then_later_fresh_failure": connected_then_later_fresh_failure,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
