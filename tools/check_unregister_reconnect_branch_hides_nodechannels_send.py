#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def main() -> int:
    if len(sys.argv) != 5:
        print(
            "usage: check_unregister_reconnect_branch_hides_nodechannels_send.py "
            "<ClusterConnectionManager.java> <stdout.log> <report.json> <nodechannels-check.json>",
            file=sys.stderr,
        )
        return 2

    cluster_connection_manager = Path(sys.argv[1]).read_text()
    stdout_text = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())
    nodechannels = json.loads(Path(sys.argv[4]).read_text())

    source_close_listener_unregisters = (
        'conn.addCloseListener(ActionListener.wrap(() -> {' in cluster_connection_manager
        and 'connectedNodes.remove(node, finalConnection);' in cluster_connection_manager
        and 'connectionListener.onNodeDisconnected(node, conn);' in cluster_connection_manager
    )

    cluster_unregister_count = count(stdout_text, r"unregistering .* after connection close and marking as disconnected")
    connector_full_connection_count = count(stdout_text, r"completed full connection with \[")

    transport_handshake_first_frame_count = 0
    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        if action == "internal:transport/handshake" and row.get("follow_up_frame") is None:
            transport_handshake_first_frame_count += 1

    result = "unregister_reconnect_branch_inconclusive"
    if (
        source_close_listener_unregisters
        and nodechannels.get("result")
        == "current_mixed_runtime_still_does_not_observe_java_side_nodechannels_getchannel_send_path_and_only_observes_inbound_fresh_first_frame_sockets"
        and cluster_unregister_count > 0
        and connector_full_connection_count > 0
        and transport_handshake_first_frame_count > 0
    ):
        result = (
            "close_listener_unregister_then_reconnect_branch_best_explains_why_retained_nodechannels_getchannel_send_"
            "is_not_observed_and_only_fresh_first_frame_sockets_remain"
        )

    print(
        json.dumps(
            {
                "source_close_listener_unregisters": source_close_listener_unregisters,
                "cluster_unregister_count": cluster_unregister_count,
                "connector_full_connection_count": connector_full_connection_count,
                "transport_handshake_first_frame_count": transport_handshake_first_frame_count,
                "nodechannels_result": nodechannels.get("result"),
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
