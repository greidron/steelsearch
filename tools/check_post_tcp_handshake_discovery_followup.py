#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TARGET_ACTIONS = {
    "internal:discovery/request_peers",
    "internal:cluster/request_pre_vote",
    "internal:cluster/coordination/start_join",
    "internal:cluster/coordination/join",
    "internal:cluster/coordination/join/validate",
    "internal:cluster/coordination/join/validate_compressed",
}


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_post_tcp_handshake_discovery_followup.py <probe_report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text())
    captures = report.get("steelsearch_transport_capture", [])

    matches = []
    for capture in captures:
        first_frame = capture.get("first_frame") or {}
        post_follow_up_frame = capture.get("post_follow_up_frame") or {}
        if first_frame.get("action_hint") != "internal:transport/handshake":
            continue
        if capture.get("first_post_response_event") != "handled_follow_up_request":
            continue
        action = post_follow_up_frame.get("action_hint")
        if action not in TARGET_ACTIONS:
            continue
        matches.append(
            {
                "peer_addr": capture.get("peer_addr"),
                "first_action": first_frame.get("action_hint"),
                "post_follow_up_action": action,
                "connection_end": capture.get("connection_end"),
            }
        )

    result = {
        "report_path": str(report_path),
        "match_count": len(matches),
        "matches": matches,
        "result": (
            "post_transport_handshake_same_connection_discovery_or_join_followup_observed"
            if matches
            else "post_transport_handshake_same_connection_discovery_or_join_followup_not_observed"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if matches else 1


if __name__ == "__main__":
    raise SystemExit(main())
