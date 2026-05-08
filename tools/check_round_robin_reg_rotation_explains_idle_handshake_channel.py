#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print(
            'usage: check_round_robin_reg_rotation_explains_idle_handshake_channel.py <mixed_artifact.json> <ConnectionProfile.java> <TcpTransport.java> <TransportService.java> <TransportSettings.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    connection_profile_path = Path(sys.argv[2])
    tcp_transport_path = Path(sys.argv[3])
    transport_service_path = Path(sys.argv[4])
    transport_settings_path = Path(sys.argv[5])

    with artifact_path.open() as f:
        data = json.load(f)
    connection_profile_text = connection_profile_path.read_text()
    tcp_transport_text = tcp_transport_path.read_text()
    transport_service_text = transport_service_path.read_text()
    transport_settings_text = transport_settings_path.read_text()

    capture = data['steelsearch_transport_capture']
    transport_handshake = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    reg_followup = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') in {
            'internal:discovery/request_peers',
            'internal:cluster/coordination/start_join',
        }
    ]

    handshake_without_same_socket_follow = sum(
        1 for item in transport_handshake if item.get('follow_up_frame') is None and item.get('post_follow_up_frame') is None
    )
    same_tick_reg_sibling = 0
    for handshake in transport_handshake:
        started = handshake['connection_started_at_ms']
        near = [item for item in reg_followup if 0 <= item['connection_started_at_ms'] - started <= 5]
        if near:
            same_tick_reg_sibling += 1

    source_default_reg6 = 'transport.connections_per_node.reg' in transport_settings_text and '6,' in transport_settings_text
    source_round_robin_channel_selection = 'Math.floorMod(counter.incrementAndGet(), length)' in connection_profile_text and 'getChannel(List<T> channels)' in connection_profile_text
    source_handshake_uses_empty_reg = 'HANDSHAKE_ACTION_NAME' in transport_service_text and 'TransportRequestOptions.EMPTY' in transport_service_text
    source_nodechannels_selects_channel_by_type = 'TcpChannel channel = channel(options.type());' in tcp_transport_text

    result = {
        'transport_handshake_count': len(transport_handshake),
        'transport_handshake_without_same_socket_follow_count': handshake_without_same_socket_follow,
        'same_tick_reg_sibling_count': same_tick_reg_sibling,
        'source_default_reg6': source_default_reg6,
        'source_round_robin_channel_selection': source_round_robin_channel_selection,
        'source_handshake_uses_empty_reg': source_handshake_uses_empty_reg,
        'source_nodechannels_selects_channel_by_type': source_nodechannels_selects_channel_by_type,
        'result': 'round_robin_reg_sibling_rotation_best_explains_why_handshake_used_channel_stays_idle'
        if len(transport_handshake) > 0
        and handshake_without_same_socket_follow == len(transport_handshake)
        and same_tick_reg_sibling > 0
        and source_default_reg6
        and source_round_robin_channel_selection
        and source_handshake_uses_empty_reg
        and source_nodechannels_selects_channel_by_type
        else 'artifact_and_source_do_not_yet_support_round_robin_reg_rotation_explanation',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
