#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(msg)


def count(text: str, pattern: str) -> int:
    return len(re.findall(pattern, text, re.MULTILINE))


def main() -> int:
    if len(sys.argv) != 7:
        print(
            "usage: check_nodechannels_getchannel_reachability_vs_inbound_fresh_sockets.py "
            "<PeerFinder.java> <TransportService.java> <TcpTransport.java> <RemoteConnectionManager.java> <stdout.log> <report.json>",
            file=sys.stderr,
        )
        return 2

    peerfinder = Path(sys.argv[1]).read_text()
    transport_service = Path(sys.argv[2]).read_text()
    tcp_transport = Path(sys.argv[3]).read_text()
    remote_connection_manager = Path(sys.argv[4]).read_text()
    stdout_text = Path(sys.argv[5]).read_text()
    report = json.loads(Path(sys.argv[6]).read_text())

    source_request_peers_uses_transport_service = "transportService.sendRequest(" in peerfinder and "REQUEST_PEERS_ACTION_NAME" in peerfinder
    source_transport_service_gets_connection = "connection = getConnection(node);" in transport_service and "connection.sendRequest(requestId, action, request, options);" in transport_service
    source_nodechannels_send_request_uses_getchannel = (
        "TcpChannel channel = channel(options.type());" in tcp_transport
        and "return connectionTypeHandle.getChannel(channels);" in tcp_transport
    )
    source_proxy_connection_is_remote_cluster_only = "return new ProxyConnection(getAnyRemoteConnection(), node);" in remote_connection_manager

    connection_profile_selection_count = count(stdout_text, r"selected channel index \[")
    connector_full_connection_count = count(stdout_text, r"completed full connection with \[")

    action_counts = {
        "request_peers": 0,
        "follower_check": 0,
        "publish_state": 0,
    }
    first_frame_only_counts = {
        "request_peers": 0,
        "follower_check": 0,
        "publish_state": 0,
    }

    for conn in report.get("steelsearch_transport_capture", []) or []:
        first_frame = conn.get("first_frame")
        if isinstance(first_frame, dict):
            action = first_frame.get("action_hint")
        else:
            action = first_frame
        if action == "internal:discovery/request_peers":
            key = "request_peers"
        elif action == "internal:coordination/fault_detection/follower_check":
            key = "follower_check"
        elif action == "internal:cluster/coordination/publish_state":
            key = "publish_state"
        else:
            continue
        action_counts[key] += 1
        if conn.get("follow_up_frame") is None and conn.get("post_follow_up_frame") is None:
            first_frame_only_counts[key] += 1

    runtime_only_shows_inbound_fresh_first_frames = (
        action_counts["request_peers"] > 0
        and action_counts == first_frame_only_counts
    )

    require(source_request_peers_uses_transport_service, "expected PeerFinder requestPeers transportService.sendRequest path")
    require(source_transport_service_gets_connection, "expected TransportService getConnection/sendRequest path")
    require(source_nodechannels_send_request_uses_getchannel, "expected NodeChannels getChannel send path")
    require(source_proxy_connection_is_remote_cluster_only, "expected ProxyConnection remote-cluster-only source hook")

    if (
        connection_profile_selection_count == 0
        and connector_full_connection_count > 0
        and runtime_only_shows_inbound_fresh_first_frames
    ):
        result = (
            "current_mixed_runtime_still_does_not_observe_java_side_nodechannels_getchannel_send_path_"
            "and_only_observes_inbound_fresh_first_frame_sockets"
        )
    else:
        result = "nodechannels_getchannel_runtime_reachability_inconclusive"

    print(
        json.dumps(
            {
                "source_request_peers_uses_transport_service_send_request": source_request_peers_uses_transport_service,
                "source_transport_service_gets_connection_then_send_request": source_transport_service_gets_connection,
                "source_nodechannels_send_request_uses_getchannel": source_nodechannels_send_request_uses_getchannel,
                "source_proxy_connection_is_remote_cluster_only": source_proxy_connection_is_remote_cluster_only,
                "connection_profile_selection_count": connection_profile_selection_count,
                "connector_full_connection_count": connector_full_connection_count,
                "action_counts": action_counts,
                "first_frame_only_counts": first_frame_only_counts,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
