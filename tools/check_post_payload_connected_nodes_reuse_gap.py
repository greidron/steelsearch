#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: check_post_payload_connected_nodes_reuse_gap.py <TransportService.java> <ClusterConnectionManager.java> <report.json>"
        )

    transport_service = Path(sys.argv[1]).read_text()
    connection_manager = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_send_request_uses_get_connection = "sendRequest(" in transport_service and "getConnection(node)" in transport_service
    source_has_connected_nodes_registration = "connectedNodes.putIfAbsent" in connection_manager and "connectedNodes.remove" in connection_manager

    summary = {}
    for action_name in [
        "internal:coordination/fault_detection/follower_check",
        "internal:cluster/coordination/publish_state",
    ]:
        entries = [
            entry
            for entry in report["steelsearch_transport_capture"]
            if (entry.get("first_frame") or {}).get("action_hint") == action_name
        ]
        summary[action_name] = {
            "count": len(entries),
            "first_frame_only_count": sum(
                1
                for entry in entries
                if entry.get("follow_up_frame") is None and entry.get("post_follow_up_frame") is None
            ),
        }

    follower = summary["internal:coordination/fault_detection/follower_check"]
    publish = summary["internal:cluster/coordination/publish_state"]

    result = (
        "post_payload_corrected_runtime_still_never_reaches_connected_nodes_reuse_for_late_coordinator_actions"
        if source_send_request_uses_get_connection
        and source_has_connected_nodes_registration
        and follower["count"] > 0
        and follower["first_frame_only_count"] == follower["count"]
        and publish["count"] > 0
        and publish["first_frame_only_count"] == publish["count"]
        else "connected_nodes_reuse_gap_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "source_send_request_uses_get_connection": source_send_request_uses_get_connection,
                "source_has_connected_nodes_registration": source_has_connected_nodes_registration,
                "actions": summary,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
