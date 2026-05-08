#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_probe_close_then_full_connection_explains_fresh_request_peers.py "
            "<HandshakingTransportAddressConnector.java> <ConnectionProfile.java> <report.json>",
            file=sys.stderr,
        )
        return 2

    connector = Path(sys.argv[1]).read_text()
    connection_profile = Path(sys.argv[2]).read_text()
    report = json.loads(Path(sys.argv[3]).read_text())

    source_closes_probe_connection_after_handshake = "IOUtils.closeWhileHandlingException(connection);" in connector
    source_starts_full_connection_after_probe = "transportService.connectToNode(remoteNode, new ActionListener<Void>()" in connector
    source_probe_uses_single_reg_channel = "Type.REG," in connector and "openConnection(" in connector
    source_default_profile_is_multi_channel = (
        "builder.addConnections(connectionsPerNodeBulk, TransportRequestOptions.Type.BULK);" in connection_profile
        and "builder.addConnections(connectionsPerNodePing, TransportRequestOptions.Type.PING);" in connection_profile
        and "builder.addConnections(connectionsPerNodeReg, TransportRequestOptions.Type.REG);" in connection_profile
    )

    direct_full_connect_count = 0
    request_peers_first_frame_only_count = 0
    for row in report.get("steelsearch_transport_capture", []) or []:
        first = row.get("first_frame")
        action = first.get("action_hint") if isinstance(first, dict) else first
        if action == "internal:transport/handshake":
            direct_full_connect_count += 1
        if action == "internal:discovery/request_peers" and row.get("follow_up_frame") is None and row.get("post_follow_up_frame") is None:
            request_peers_first_frame_only_count += 1

    if (
        source_closes_probe_connection_after_handshake
        and source_starts_full_connection_after_probe
        and source_probe_uses_single_reg_channel
        and source_default_profile_is_multi_channel
        and direct_full_connect_count > 0
        and request_peers_first_frame_only_count > 0
    ):
        result = (
            "immediate_request_peers_on_separate_fresh_socket_is_consistent_with_source_because_probe_handshake_socket_is_closed_"
            "before_full_multi_channel_connection_and_is_not_expected_to_be_reused"
        )
    else:
        result = "probe_close_then_full_connection_explanation_inconclusive"

    print(
        json.dumps(
            {
                "source_closes_probe_connection_after_handshake": source_closes_probe_connection_after_handshake,
                "source_starts_full_connection_after_probe": source_starts_full_connection_after_probe,
                "source_probe_uses_single_reg_channel": source_probe_uses_single_reg_channel,
                "source_default_profile_is_multi_channel": source_default_profile_is_multi_channel,
                "direct_full_connect_count": direct_full_connect_count,
                "request_peers_first_frame_only_count": request_peers_first_frame_only_count,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
