#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_scheduled_reprobe_never_recovers_reuse.py <peerfinder.java> <cluster_connection_manager.java> <report.json>"
        )

    peerfinder = Path(sys.argv[1]).read_text()
    cluster_conn = Path(sys.argv[2]).read_text()
    report = load_json(sys.argv[3])

    source_has_scheduled_reprobe = (
        "scheduleUnlessShuttingDown(findPeersInterval" in peerfinder
        and "startProbe(discoveryNodeObjectCursor.getAddress());" in peerfinder
        and "providedAddresses.forEach(this::startProbe);" in peerfinder
    )
    source_has_close_listener_unregister = (
        "conn.addCloseListener" in cluster_conn
        and "connectedNodes.remove(node, finalConnection);" in cluster_conn
        and "connectionListener.onNodeDisconnected(node, conn);" in cluster_conn
    )

    capture = report.get("steelsearch_transport_capture") or []
    direct_full_connect = [
        entry for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]
    pre_post_request_remote_eof = [
        entry for entry in direct_full_connect
        if entry.get("first_post_response_event") == "remote_eof"
        and entry.get("post_follow_up_frame") is None
    ]

    result = (
        "scheduled_peerfinder_reprobe_reaches_same_direct_full_connect_remote_eof_and_immediate_unregister_loop_instead_of_recovering_connected_nodes_reuse"
        if source_has_scheduled_reprobe
        and source_has_close_listener_unregister
        and len(direct_full_connect) > 0
        and len(pre_post_request_remote_eof) == len(direct_full_connect)
        else "scheduled_reprobe_recovery_gap_not_fully_established"
    )

    print(json.dumps({
        "source_has_scheduled_reprobe": source_has_scheduled_reprobe,
        "source_has_close_listener_unregister": source_has_close_listener_unregister,
        "direct_full_connect_count": len(direct_full_connect),
        "pre_post_request_remote_eof_count": len(pre_post_request_remote_eof),
        "result": result,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
