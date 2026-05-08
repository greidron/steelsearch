#!/usr/bin/env python3
import json
import re
import sys
from datetime import datetime
from pathlib import Path

TS_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]")
TARGET_RE = re.compile(r"\{rust-replica-1\}.*\{127\.0\.0\.1\}\{127\.0\.0\.1:(?P<port>\d+)\}")


def parse_ms(line: str):
    m = TS_RE.match(line)
    if not m:
        return None
    ts = m.group("ts")
    dt = datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S,%f")
    return int(dt.timestamp() * 1000)


def read_text(path: str) -> str:
    return Path(path).read_text()


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_whole_burst_close_matches_node_disconnect_policy.py "
            "<ClusterConnectionManager.java> <FollowersChecker.java> <NodeConnectionsService.java> <stdout.log>",
            file=sys.stderr,
        )
        return 2

    cluster_src = read_text(sys.argv[1])
    follower_src = read_text(sys.argv[2])
    node_conn_src = read_text(sys.argv[3])
    lines = Path(sys.argv[4]).read_text().splitlines()

    source_has_close_listener_unregister = "after connection close and marking as disconnected" in cluster_src
    source_has_on_node_disconnected = "onNodeDisconnected(node, conn)" in cluster_src
    source_followers_checker_disconnect_fail = (
        'handleDisconnectedNode(DiscoveryNode discoveryNode)' in follower_src
        and 'followerChecker.failNode("disconnected")' in follower_src
    )
    source_has_disconnect_reconnect_policy = (
        "transportService.disconnectFromNode(discoveryNode);" in node_conn_src
        and 'onCompletion(ActivityType.DISCONNECTING, null, connectActivity);' in node_conn_src
    )

    events = []
    target_ports = set()
    for idx, line in enumerate(lines):
        ms = parse_ms(line)
        if ms is None:
            continue
        target = TARGET_RE.search(line)
        if target:
            target_ports.add(target.group("port"))
        kind = None
        if "unregistering {rust-replica-1}" in line and "after connection close and marking as disconnected" in line:
            kind = "unregister"
        elif "FollowerChecker{" in line and " disconnected" in line and "rust-replica-1" in line:
            kind = "follower_disconnected"
        elif "FollowerChecker{" in line and " marking node as faulty" in line and "rust-replica-1" in line:
            kind = "marking_faulty"
        elif "connecting to node [{rust-replica-1}" in line:
            kind = "connecting"
        elif "completed full connection with [{rust-replica-1}" in line:
            kind = "completed_full_connection"
        if kind:
            events.append({"ms": ms, "kind": kind, "line": idx + 1})

    cycle_count = 0
    disconnected_after_unregister = 0
    faulty_after_unregister = 0
    reconnect_after_unregister = 0
    completed_after_unregister = 0

    for i, event in enumerate(events):
        if event["kind"] != "unregister":
            continue
        cycle_count += 1
        base = event["ms"]
        window = events[i + 1 :]
        next_disconnected = next((e for e in window if e["kind"] == "follower_disconnected" and 0 <= e["ms"] - base <= 150), None)
        next_faulty = next((e for e in window if e["kind"] == "marking_faulty" and 0 <= e["ms"] - base <= 250), None)
        next_connecting = next((e for e in window if e["kind"] == "connecting" and 0 <= e["ms"] - base <= 1500), None)
        next_completed = next((e for e in window if e["kind"] == "completed_full_connection" and 0 <= e["ms"] - base <= 2000), None)
        if next_disconnected:
            disconnected_after_unregister += 1
        if next_faulty:
            faulty_after_unregister += 1
        if next_connecting:
            reconnect_after_unregister += 1
        if next_completed:
            completed_after_unregister += 1

    if (
        cycle_count > 0
        and disconnected_after_unregister > 0
        and reconnect_after_unregister > 0
        and source_has_close_listener_unregister
        and source_has_on_node_disconnected
        and source_followers_checker_disconnect_fail
        and source_has_disconnect_reconnect_policy
    ):
        result = (
            "peer_side_whole_burst_close_is_better_explained_as_java_node_level_disconnect_fault_and_reconnect_policy_"
            "than_as_a_handshake_channel_specific_decision"
        )
    else:
        result = "whole_burst_close_policy_mapping_inconclusive"

    print(json.dumps({
        "source_has_close_listener_unregister": source_has_close_listener_unregister,
        "source_has_on_node_disconnected": source_has_on_node_disconnected,
        "source_followers_checker_disconnect_fail": source_followers_checker_disconnect_fail,
        "source_has_disconnect_reconnect_policy": source_has_disconnect_reconnect_policy,
        "target_ports": sorted(target_ports),
        "cycle_count": cycle_count,
        "disconnected_after_unregister_count": disconnected_after_unregister,
        "faulty_after_unregister_count": faulty_after_unregister,
        "reconnect_after_unregister_count": reconnect_after_unregister,
        "completed_after_unregister_count": completed_after_unregister,
        "result": result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
