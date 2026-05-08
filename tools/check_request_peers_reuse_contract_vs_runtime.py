#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 5:
        raise SystemExit(
            "usage: check_request_peers_reuse_contract_vs_runtime.py "
            "<peerfinder.java> <transport_service.java> <cluster_connection_manager.java> <report.json>"
        )

    peerfinder = Path(sys.argv[1]).read_text()
    transport_service = Path(sys.argv[2]).read_text()
    cluster_conn = Path(sys.argv[3]).read_text()
    report = load_json(sys.argv[4])

    source_request_peers_uses_send_request = (
        "transportService.sendRequest(" in peerfinder
        and "REQUEST_PEERS_ACTION_NAME" in peerfinder
    )
    source_send_request_uses_get_connection = (
        "return connectionManager.getConnection(node);" in transport_service
    )
    source_get_connection_requires_connected_node = (
        'throw new NodeNotConnectedException(node, "Node not connected");' in cluster_conn
    )

    capture = report.get("steelsearch_transport_capture") or []
    action_counts = {}
    first_frame_only_counts = {}
    for action in [
        "internal:discovery/request_peers",
        "internal:coordination/fault_detection/follower_check",
        "internal:cluster/coordination/publish_state",
    ]:
        entries = [e for e in capture if (e.get("first_frame") or {}).get("action_hint") == action]
        action_counts[action] = len(entries)
        first_frame_only_counts[action] = sum(1 for e in entries if e.get("follow_up_frame") is None)

    runtime_fresh_socket_only = all(
        action_counts[action] > 0 and action_counts[action] == first_frame_only_counts[action]
        for action in action_counts
    )

    result = (
        "source_requires_retained_get_connection_for_request_peers_but_runtime_shows_only_fresh_first_frame_sockets_so_retained_channel_is_already_gone_by_request_time"
        if source_request_peers_uses_send_request
        and source_send_request_uses_get_connection
        and source_get_connection_requires_connected_node
        and runtime_fresh_socket_only
        else "request_peers_reuse_contract_vs_runtime_not_fully_established"
    )

    print(json.dumps({
        "source_request_peers_uses_send_request": source_request_peers_uses_send_request,
        "source_send_request_uses_get_connection": source_send_request_uses_get_connection,
        "source_get_connection_requires_connected_node": source_get_connection_requires_connected_node,
        "action_counts": action_counts,
        "first_frame_only_counts": first_frame_only_counts,
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
