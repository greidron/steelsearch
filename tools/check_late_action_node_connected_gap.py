#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_late_action_node_connected_gap.py <TransportService.java> <ClusterConnectionManager.java> <report.json>"
        )

    transport_service = Path(sys.argv[1]).read_text()
    connection_manager = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_send_request_fails_if_not_connected = (
        "connection = getConnection(node);" in transport_service
        and "catch (final NodeNotConnectedException ex)" in transport_service
        and "handler.handleException(ex);" in transport_service
    )
    source_node_connected_is_connected_nodes_contains = "return connectedNodes.containsKey(node);" in connection_manager

    counts = {}
    for entry in report["steelsearch_transport_capture"]:
        action = (entry.get("first_frame") or {}).get("action_hint")
        if not action:
            continue
        counts[action] = counts.get(action, 0) + 1

    late_actions = {
        "internal:coordination/fault_detection/follower_check",
        "internal:cluster/coordination/publish_state",
    }
    late_actions_all_first_frame_only = True
    late_action_counts = {}
    for action in late_actions:
        entries = [
            entry
            for entry in report["steelsearch_transport_capture"]
            if (entry.get("first_frame") or {}).get("action_hint") == action
        ]
        late_action_counts[action] = len(entries)
        if not entries or not all(
            entry.get("follow_up_frame") is None and entry.get("post_follow_up_frame") is None
            for entry in entries
        ):
            late_actions_all_first_frame_only = False

    result = (
        "late_actions_still_arrive_on_new_sockets_so_current_mixed_runtime_never_reaches_nodeConnected_getConnection_reuse"
        if source_send_request_fails_if_not_connected
        and source_node_connected_is_connected_nodes_contains
        and counts.get("internal:transport/handshake", 0) > 0
        and late_actions_all_first_frame_only
        else "late_action_node_connected_gap_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "source_send_request_fails_if_not_connected": source_send_request_fails_if_not_connected,
                "source_node_connected_is_connected_nodes_contains": source_node_connected_is_connected_nodes_contains,
                "transport_handshake_first_frame_count": counts.get("internal:transport/handshake", 0),
                "late_action_counts": late_action_counts,
                "late_actions_all_first_frame_only": late_actions_all_first_frame_only,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
