#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 6:
        print(
            'usage: check_handshake_channel_isolated_from_reg_state_sibling_traffic.py <mixed_artifact.json> <ConnectionProfile.java> <JoinHelper.java> <TransportRequestOptions.java> <PublicationTransportHandler.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    connection_profile_path = Path(sys.argv[2])
    join_helper_path = Path(sys.argv[3])
    transport_request_options_path = Path(sys.argv[4])
    publication_handler_path = Path(sys.argv[5])

    with artifact_path.open() as f:
        data = json.load(f)
    connection_profile_text = connection_profile_path.read_text()
    join_helper_text = join_helper_path.read_text()
    transport_request_options_text = transport_request_options_path.read_text()
    publication_handler_text = publication_handler_path.read_text()

    capture = data['steelsearch_transport_capture']
    transport_handshake = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    request_peers = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:discovery/request_peers'
    ]
    start_join = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:cluster/coordination/start_join'
    ]
    publish_state = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:cluster/coordination/publish_state'
    ]

    no_same_socket_follow = [
        item for item in transport_handshake
        if item.get('follow_up_frame') is None and item.get('post_follow_up_frame') is None
    ]
    dwell_gaps = [item['connection_end_at_ms'] - item['response_frame_sent_at_ms'] for item in no_same_socket_follow]

    reg_state_sibling_delta = []
    sibling_candidates = request_peers + start_join + publish_state
    for handshake in transport_handshake:
        started = handshake['connection_started_at_ms']
        near = [item for item in sibling_candidates if 0 <= item['connection_started_at_ms'] - started <= 5]
        if near:
            reg_state_sibling_delta.append(min(item['connection_started_at_ms'] for item in near) - started)

    source_default_has_multiple_reg = 'builder.addConnections(connectionsPerNodeReg, TransportRequestOptions.Type.REG);' in connection_profile_text
    source_request_options_empty_defaults_reg = 'private Type type = Type.REG;' in transport_request_options_text
    source_start_join_uses_empty = 'transportService.sendRequest(destination, START_JOIN_ACTION_NAME, startJoinRequest' in join_helper_text
    source_publish_state_uses_state = '.withType(TransportRequestOptions.Type.STATE)' in publication_handler_text

    result = {
        'transport_handshake_count': len(transport_handshake),
        'transport_handshake_without_same_socket_follow_count': len(no_same_socket_follow),
        'transport_handshake_response_to_eof_gap_ms': {
            'min': min(dwell_gaps),
            'median': statistics.median(dwell_gaps),
            'max': max(dwell_gaps),
        } if dwell_gaps else None,
        'same_tick_reg_or_state_sibling_count': len(reg_state_sibling_delta),
        'source_default_has_multiple_reg': source_default_has_multiple_reg,
        'source_request_options_empty_defaults_reg': source_request_options_empty_defaults_reg,
        'source_start_join_uses_empty_reg': source_start_join_uses_empty,
        'source_publish_state_uses_state': source_publish_state_uses_state,
        'result': 'handshake_used_channel_isolated_while_reg_state_sibling_channels_receive_later_actions'
        if len(no_same_socket_follow) == len(transport_handshake)
        and len(reg_state_sibling_delta) > 0
        and source_default_has_multiple_reg
        and source_request_options_empty_defaults_reg
        and source_start_join_uses_empty
        and source_publish_state_uses_state
        else 'artifact_and_source_do_not_yet_show_handshake_channel_isolation_from_sibling_traffic',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
