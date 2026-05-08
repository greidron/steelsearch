#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_first_request_peers_attempt_is_already_fresh_socket.py "
            "<PeerFinder.java> <stdout.log> <report.json>",
            file=sys.stderr,
        )
        return 2

    peerfinder = Path(sys.argv[1]).read_text()
    stdout_text = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_establish_connection_immediately_requests_peers = (
        "discoveryNode.set(remoteNode);" in peerfinder and "requestPeers();" in peerfinder
    )

    completed_full_connection_count = count(stdout_text, r"completed full connection with \[")
    requesting_peers_log_count = count(stdout_text, r"requesting peers")
    unregister_count = count(stdout_text, r"unregistering .* after connection close and marking as disconnected")

    request_peers_count = 0
    request_peers_first_frame_only_count = 0
    direct_full_connect_count = 0
    direct_full_connect_no_post_frame_count = 0

    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        if action == "internal:discovery/request_peers":
            request_peers_count += 1
            if row.get("follow_up_frame") is None and row.get("post_follow_up_frame") is None:
                request_peers_first_frame_only_count += 1
        if action == "internal:transport/handshake":
            direct_full_connect_count += 1
            if row.get("follow_up_frame") is None and row.get("post_follow_up_frame") is None:
                direct_full_connect_no_post_frame_count += 1

    if (
        source_establish_connection_immediately_requests_peers
        and completed_full_connection_count > 0
        and requesting_peers_log_count >= completed_full_connection_count
        and request_peers_count > 0
        and request_peers_count == request_peers_first_frame_only_count
        and direct_full_connect_count > 0
        and direct_full_connect_no_post_frame_count >= direct_full_connect_count - 1
    ):
        result = (
            "first_eligible_request_peers_attempt_is_already_observed_as_separate_fresh_first_frame_socket_"
            "while_direct_full_connect_socket_stays_handshake_only_until_unregister"
        )
    else:
        result = "first_request_peers_fresh_socket_hypothesis_inconclusive"

    print(
        json.dumps(
            {
                "source_establish_connection_immediately_requests_peers": source_establish_connection_immediately_requests_peers,
                "completed_full_connection_count": completed_full_connection_count,
                "requesting_peers_log_count": requesting_peers_log_count,
                "unregister_count": unregister_count,
                "request_peers_count": request_peers_count,
                "request_peers_first_frame_only_count": request_peers_first_frame_only_count,
                "direct_full_connect_count": direct_full_connect_count,
                "direct_full_connect_no_post_frame_count": direct_full_connect_no_post_frame_count,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
