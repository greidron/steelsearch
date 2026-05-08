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
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: check_unregistration_callback_boundary.py "
            "<cluster_connection_manager.java> <connection_manager.java> <followers_checker.java> <stdout.log>"
        )

    cluster_conn = Path(sys.argv[1]).read_text()
    conn_mgr = Path(sys.argv[2]).read_text()
    followers = Path(sys.argv[3]).read_text()
    lines = Path(sys.argv[4]).read_text().splitlines()

    source_has_close_listener_to_node_disconnected = (
        "conn.addCloseListener" in cluster_conn
        and "connectedNodes.remove(node, finalConnection);" in cluster_conn
        and "connectionListener.onNodeDisconnected(node, conn);" in cluster_conn
    )
    source_has_delegating_forward = "listener.onNodeDisconnected(key, connection);" in conn_mgr
    source_has_followers_checker_listener = (
        "transportService.addConnectionListener(new TransportConnectionListener()" in followers
        and "public void onNodeDisconnected(DiscoveryNode node, Transport.Connection connection) {" in followers
        and "handleDisconnectedNode(node);" in followers
        and 'followerChecker.failNode("disconnected");' in followers
    )

    requesting = []
    disconnected = []
    faulty = []
    fresh_attempt = []
    for idx, line in enumerate(lines):
        pm = PEER_RE.search(line)
        if pm and pm.group("addr") == "127.0.0.1:57743":
            if pm.group("event") == "requesting peers" and pm.group("node") != "null":
                requesting.append(idx)
            elif pm.group("event") == "attempting connection" and pm.group("node") == "null":
                fresh_attempt.append(idx)
        fm = FOLLOWER_RE.search(line)
        if fm:
            if fm.group("event") == "disconnected":
                disconnected.append(idx)
            else:
                faulty.append(idx)

    runtime_matches_callback_chain = False
    for req in requesting:
        later_disc = [d for d in disconnected if d > req]
        if not later_disc:
            continue
        later_faulty = [f for f in faulty if f >= later_disc[0]]
        if not later_faulty:
            continue
        later_attempt = [a for a in fresh_attempt if a > later_faulty[0]]
        if later_attempt:
            runtime_matches_callback_chain = True
            break

    result = (
        "unregister_recreation_callback_boundary_is_connection_close_listener_to_onNodeDisconnected_to_followers_checker_failNode"
        if source_has_close_listener_to_node_disconnected
        and source_has_delegating_forward
        and source_has_followers_checker_listener
        and runtime_matches_callback_chain
        else "unregistration_callback_boundary_not_fully_established"
    )

    print(json.dumps({
        "source_has_close_listener_to_node_disconnected": source_has_close_listener_to_node_disconnected,
        "source_has_delegating_forward": source_has_delegating_forward,
        "source_has_followers_checker_listener": source_has_followers_checker_listener,
        "connected_requesting_peers_count": len(requesting),
        "follower_disconnected_count": len(disconnected),
        "follower_marking_faulty_count": len(faulty),
        "fresh_null_attempt_count": len(fresh_attempt),
        "runtime_matches_callback_chain": runtime_matches_callback_chain,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
