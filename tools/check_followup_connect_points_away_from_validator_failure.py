#!/usr/bin/env python3
import json
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_followup_connect_points_away_from_validator_failure.py <mixed_artifact.json> <TransportService.java> <ClusterConnectionManager.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    transport_service_path = Path(sys.argv[2])
    cluster_connection_manager_path = Path(sys.argv[3])

    with artifact_path.open() as f:
        data = json.load(f)
    transport_service_text = transport_service_path.read_text()
    cluster_connection_manager_text = cluster_connection_manager_path.read_text()

    capture = data['steelsearch_transport_capture']
    full_connect = [
        item for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    ]
    response_to_eof_gaps = [
        item['connection_end_at_ms'] - item['response_frame_sent_at_ms']
        for item in full_connect
        if item.get('response_frame_sent_at_ms') is not None
    ]

    source_validator_is_handshake = 'handshake(newConnection, actualProfile.getHandshakeTimeout().millis()' in transport_service_text
    source_validator_failure_closes_immediately = 'IOUtils.closeWhileHandlingException(conn);' in cluster_connection_manager_text and 'failConnectionListeners(node, releaseOnce, e, currentListener);' in cluster_connection_manager_text

    result = {
        'transport_handshake_count': len(full_connect),
        'response_to_eof_gap_ms': {
            'min': min(response_to_eof_gaps),
            'median': statistics.median(response_to_eof_gaps),
            'max': max(response_to_eof_gaps),
        } if response_to_eof_gaps else None,
        'source_validator_is_transport_handshake': source_validator_is_handshake,
        'source_validator_failure_closes_connection_immediately': source_validator_failure_closes_immediately,
        'result': 'followup_connect_artifact_points_away_from_validator_failure_and_toward_post_validation_connection_loss'
        if response_to_eof_gaps and min(response_to_eof_gaps) >= 700 and source_validator_is_handshake and source_validator_failure_closes_immediately
        else 'artifact_does_not_rule_out_validator_failure',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
