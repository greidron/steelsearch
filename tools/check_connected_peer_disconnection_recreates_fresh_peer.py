#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


PEER_RE = re.compile(
    r"Peer\{transportAddress=(?P<addr>[^,]+), discoveryNode=(?P<node>.+?), peersRequestInFlight=(?P<inflight>[^}]+)\} (?P<event>requesting peers|attempting connection)"
)
FOLLOWER_RE = re.compile(
    r"FollowerChecker\{discoveryNode=\{rust-replica-1\}\{rust-replica-1\}\{rust-replica-1-ephemeral\}\{127.0.0.1\}\{127.0.0.1:57743\}.*\} (?P<event>disconnected|marking node as faulty)"
)


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_connected_peer_disconnection_recreates_fresh_peer.py <cluster_connection_manager.java> <stdout.log>"
        )

    source = Path(sys.argv[1]).read_text()
    lines = Path(sys.argv[2]).read_text().splitlines()

    source_has_close_unregister = (
        "conn.addCloseListener" in source
        and "connectedNodes.remove(node, finalConnection);" in source
        and "onNodeDisconnected(node, conn);" in source
    )

    requesting_lines = []
    follower_disconnect_lines = []
    follower_faulty_lines = []
    fresh_null_attempt_lines = []

    for idx, line in enumerate(lines):
        peer_match = PEER_RE.search(line)
        if peer_match and peer_match.group("addr") == "127.0.0.1:57743":
            if peer_match.group("event") == "requesting peers" and peer_match.group("node") != "null":
                requesting_lines.append(idx)
            if peer_match.group("event") == "attempting connection" and peer_match.group("node") == "null":
                fresh_null_attempt_lines.append(idx)

        follower_match = FOLLOWER_RE.search(line)
        if follower_match:
            if follower_match.group("event") == "disconnected":
                follower_disconnect_lines.append(idx)
            elif follower_match.group("event") == "marking node as faulty":
                follower_faulty_lines.append(idx)

    connected_then_disconnected_then_fresh_attempt = False
    for req in requesting_lines:
        later_disc = [d for d in follower_disconnect_lines if d > req]
        if not later_disc:
            continue
        later_attempt = [a for a in fresh_null_attempt_lines if a > later_disc[0]]
        if later_attempt:
            connected_then_disconnected_then_fresh_attempt = True
            break

    result = (
        "connected_peer_is_unsettled_by_disconnection_fault_path_and_then_recreated_as_fresh_null_discovery_peer"
        if source_has_close_unregister
        and requesting_lines
        and follower_disconnect_lines
        and follower_faulty_lines
        and fresh_null_attempt_lines
        and connected_then_disconnected_then_fresh_attempt
        else "connected_peer_disconnection_to_fresh_peer_recreation_not_fully_established"
    )

    print(json.dumps({
        "source_has_close_listener_unregister_path": source_has_close_unregister,
        "connected_requesting_peers_count": len(requesting_lines),
        "follower_disconnected_count": len(follower_disconnect_lines),
        "follower_marking_faulty_count": len(follower_faulty_lines),
        "fresh_null_attempt_count": len(fresh_null_attempt_lines),
        "connected_then_disconnected_then_fresh_attempt": connected_then_disconnected_then_fresh_attempt,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
