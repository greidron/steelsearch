#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def summarize_capture(path: str):
    captures = json.loads(Path(path).read_text())
    counts = {"tcp": 0, "transport": 0, "request_peers": 0, "tcp_no_follow_up": 0}
    for row in captures:
        first = row.get("first_frame") or {}
        hint = first.get("action_hint")
        if hint == "internal:tcp/handshake":
            counts["tcp"] += 1
            if row.get("follow_up_frame") is None and row.get("first_post_response_event") == "remote_eof":
                counts["tcp_no_follow_up"] += 1
        elif hint == "internal:transport/handshake":
            counts["transport"] += 1
        elif hint == "internal:discovery/request_peers":
            counts["request_peers"] += 1
    return counts


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_discovery_regression_stops_after_tcp_handshake.py <main.rs> <capture-a> <capture-b>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text()
    a = summarize_capture(sys.argv[2])
    b = summarize_capture(sys.argv[3])

    source_has_follow_ups = (
        'Some("internal:transport/handshake")' in source
        and 'Some("internal:discovery/request_peers")' in source
    )

    print(f"source_has_follow_ups={source_has_follow_ups}")
    print(f"run_a={a}")
    print(f"run_b={b}")

    if (
        source_has_follow_ups
        and a["tcp"] > 0
        and b["tcp"] > 0
        and a["transport"] == 0
        and b["transport"] == 0
        and a["request_peers"] == 0
        and b["request_peers"] == 0
        and a["tcp_no_follow_up"] == a["tcp"]
        and b["tcp_no_follow_up"] == b["tcp"]
    ):
        print(
            "discovery_regression_stops_after_tcp_handshake_before_transport_handshake_or_request_peers_follow_up"
        )
        return 0

    print("inconclusive_discovery_stop_point")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
