#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_multichannel_profile_allows_fresh_sibling_sockets_after_registration.py <mixed_artifact.json> <ConnectionProfile.java> <TransportSettings.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    connection_profile_path = Path(sys.argv[2])
    transport_settings_path = Path(sys.argv[3])

    with artifact_path.open() as f:
        data = json.load(f)
    connection_profile_text = connection_profile_path.read_text()
    transport_settings_text = transport_settings_path.read_text()

    capture = data['steelsearch_transport_capture']
    transport_handshake = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    reg_family = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') in {
            'internal:discovery/request_peers',
            'internal:cluster/coordination/start_join',
            'internal:cluster/coordination/publish_state',
        }
    ]

    sibling_open_deltas = []
    for handshake in transport_handshake:
        started = handshake['connection_started_at_ms']
        near = [
            item for item in reg_family
            if 0 <= item['connection_started_at_ms'] - started <= 120
        ]
        if near:
            sibling_open_deltas.append(min(item['connection_started_at_ms'] for item in near) - started)

    source_default_profile_is_multichannel = (
        'builder.addConnections(connectionsPerNodeBulk, TransportRequestOptions.Type.BULK);' in connection_profile_text
        and 'builder.addConnections(connectionsPerNodePing, TransportRequestOptions.Type.PING);' in connection_profile_text
        and 'builder.addConnections(connectionsPerNodeReg, TransportRequestOptions.Type.REG);' in connection_profile_text
    )
    source_single_channel_probe_is_separate = 'builder.addConnections(1, channelType);' in connection_profile_text
    source_reg_default_exists = 'CONNECTIONS_PER_NODE_REG' in transport_settings_text

    result = {
        'transport_handshake_count': len(transport_handshake),
        'nearby_reg_or_coordination_sibling_count': len(sibling_open_deltas),
        'sibling_open_delta_ms': {
            'min': min(sibling_open_deltas),
            'median': statistics.median(sibling_open_deltas),
            'max': max(sibling_open_deltas),
        } if sibling_open_deltas else None,
        'source_default_profile_is_multichannel': source_default_profile_is_multichannel,
        'source_single_channel_probe_is_separate': source_single_channel_probe_is_separate,
        'source_reg_default_exists': source_reg_default_exists,
        'result': 'fresh_request_peers_start_join_sockets_are_compatible_with_registered_multichannel_siblings_not_necessarily_whole_connection_loss'
        if sibling_open_deltas and min(sibling_open_deltas) == 0 and source_default_profile_is_multichannel and source_single_channel_probe_is_separate and source_reg_default_exists
        else 'artifact_does_not_show_registered_multichannel_sibling_behavior',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
