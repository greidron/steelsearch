#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_discovery_followup_stops_at_one_shot_hold_open.py "
            "<main.rs> <transport-seed-capture.json>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    capture = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    source_has_transport_handshake_false = (
        'action_hint.as_deref() == Some("internal:transport/handshake")' in source
        and "hold_transport_channel_open(" in source
        and 'Some("internal:transport/handshake")' in source
    )
    source_has_request_peers_false = (
        'action_hint.as_deref() == Some("internal:discovery/request_peers")' in source
    )

    tcp_handshake_only = 0
    tcp_handshake_follow_up = 0
    for item in capture:
        first = item.get("first_frame") or {}
        if first.get("action_hint") == "internal:tcp/handshake":
            tcp_handshake_only += 1
            if item.get("follow_up_frame") is not None:
                tcp_handshake_follow_up += 1

    print(f"source_has_transport_handshake_branch={source_has_transport_handshake_false}")
    print(f"source_has_request_peers_branch={source_has_request_peers_false}")
    print(f"tcp_handshake_only={tcp_handshake_only}")
    print(f"tcp_handshake_follow_up={tcp_handshake_follow_up}")

    if (
        source_has_transport_handshake_false
        and source_has_request_peers_false
        and tcp_handshake_only > 0
        and tcp_handshake_follow_up == 0
    ):
        print(
            "checker_result=discovery_followup_currently_stops_at_one_shot_hold_open_before_transport_handshake_or_request_peers"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
