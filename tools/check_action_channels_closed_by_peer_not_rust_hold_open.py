#!/usr/bin/env python3
import json
import sys
from pathlib import Path


ACTIONS = {
    "internal:discovery/request_peers": "request_peers",
    "internal:coordination/fault_detection/follower_check": "follower_check",
    "internal:cluster/coordination/publish_state": "publish_state",
}


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_action_channels_closed_by_peer_not_rust_hold_open.py <main.rs> <report.json>",
            file=sys.stderr,
        )
        return 2

    main_rs = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_request_peers_uses_hold_open = 'Some("internal:discovery/request_peers")' in main_rs and "Duration::from_secs(15)" in main_rs
    source_follower_check_uses_hold_open = 'Some("internal:coordination/fault_detection/follower_check")' in main_rs and "Duration::from_secs(20)" in main_rs
    source_publish_state_uses_hold_open = 'Some("internal:cluster/coordination/publish_state")' in main_rs and "Duration::from_secs(20)" in main_rs
    source_hold_open_waits_for_peer_events = "while started.elapsed() < hold_for" in main_rs and 'TransportSeedFrameRead::Eof' in main_rs

    action_counts = {v: 0 for v in ACTIONS.values()}
    remote_eof_counts = {v: 0 for v in ACTIONS.values()}

    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        key = ACTIONS.get(action)
        if key is None:
            continue
        action_counts[key] += 1
        if row.get("first_post_response_event") == "remote_eof":
            remote_eof_counts[key] += 1

    if (
        source_request_peers_uses_hold_open
        and source_follower_check_uses_hold_open
        and source_publish_state_uses_hold_open
        and source_hold_open_waits_for_peer_events
        and action_counts == remote_eof_counts
        and action_counts["request_peers"] > 0
    ):
        result = (
            "full_connection_action_channels_are_closed_by_peer_remote_eof_while_rust_explicitly_tries_to_hold_them_open"
        )
    else:
        result = "action_channel_peer_close_vs_rust_hold_open_inconclusive"

    print(
        json.dumps(
            {
                "source_request_peers_uses_hold_open": source_request_peers_uses_hold_open,
                "source_follower_check_uses_hold_open": source_follower_check_uses_hold_open,
                "source_publish_state_uses_hold_open": source_publish_state_uses_hold_open,
                "source_hold_open_waits_for_peer_events": source_hold_open_waits_for_peer_events,
                "action_counts": action_counts,
                "remote_eof_counts": remote_eof_counts,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
