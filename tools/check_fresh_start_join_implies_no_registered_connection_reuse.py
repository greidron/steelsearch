#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_fresh_start_join_implies_no_registered_connection_reuse.py <mixed_artifact.json> <TransportService.java> <TcpTransport.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    transport_service_path = Path(sys.argv[2])
    tcp_transport_path = Path(sys.argv[3])

    with artifact_path.open() as f:
        data = json.load(f)
    transport_service_text = transport_service_path.read_text()
    tcp_transport_text = tcp_transport_path.read_text()

    capture = data['steelsearch_transport_capture']
    start_join = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:cluster/coordination/start_join'
    ]
    transport_handshake = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    start_join_with_live_candidate = 0
    for action in start_join:
        action_start = action['connection_started_at_ms']
        live = [
            channel for channel in transport_handshake
            if channel['connection_started_at_ms'] <= action_start < channel['connection_end_at_ms']
        ]
        if live:
            start_join_with_live_candidate += 1

    has_sendrequest_getconnection = (
        'connection = getConnection(node);' in transport_service_text
        and 'sendRequest(connection, action, request, options, handler);' in transport_service_text
    )
    sendrequest_body_match = re.search(
        r'public void sendRequest\(long requestId, String action, TransportRequest request, TransportRequestOptions options\)'
        r'.*?TcpChannel channel = channel\(options\.type\(\)\);'
        r'.*?handshakerHandler\.sendRequest\(',
        tcp_transport_text,
        re.S,
    )
    has_nodechannels_existing_channel_send = sendrequest_body_match is not None

    result = {
        'start_join_count': len(start_join),
        'transport_handshake_count': len(transport_handshake),
        'start_join_with_live_transport_handshake_candidate': start_join_with_live_candidate,
        'source_transportservice_sendrequest_uses_getconnection': has_sendrequest_getconnection,
        'source_nodechannels_sendrequest_uses_existing_channel': has_nodechannels_existing_channel_send,
        'result': 'fresh_start_join_sockets_imply_registered_connection_reuse_is_not_happening_and_point_away_from_profile_type_mismatch'
        if start_join_with_live_candidate > 0 and has_sendrequest_getconnection and has_nodechannels_existing_channel_send
        else 'artifact_and_source_do_not_yet_pin_this_on_registered_connection_reuse_failure',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
