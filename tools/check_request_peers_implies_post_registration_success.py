#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            'usage: check_request_peers_implies_post_registration_success.py <mixed_artifact.json> <HandshakingTransportAddressConnector.java> <PeerFinder.java> <ClusterConnectionManager.java>',
            file=sys.stderr,
        )
        return 2

    artifact_path = Path(sys.argv[1])
    connector_path = Path(sys.argv[2])
    peerfinder_path = Path(sys.argv[3])
    cluster_connection_manager_path = Path(sys.argv[4])

    with artifact_path.open() as f:
        data = json.load(f)
    connector_text = connector_path.read_text()
    peerfinder_text = peerfinder_path.read_text()
    cluster_connection_manager_text = cluster_connection_manager_path.read_text()

    capture = data['steelsearch_transport_capture']
    request_peers_count = sum(
        1
        for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:discovery/request_peers'
    )

    source_connector_onresponse_after_connecttonode = (
        'transportService.connectToNode(remoteNode, new ActionListener<Void>() {' in connector_text
        and 'listener.onResponse(remoteNode);' in connector_text
        and 'completed full connection with' in connector_text
    )
    source_peerfinder_requests_peers_after_connector_success = (
        'discoveryNode.set(remoteNode);' in peerfinder_text and 'requestPeers();' in peerfinder_text
    )
    source_registration_happens_before_listener_success = (
        'connectedNodes.putIfAbsent(node, conn)' in cluster_connection_manager_text
        and 'future.onResponse(null);' in cluster_connection_manager_text
    )

    result = {
        'request_peers_first_frame_count': request_peers_count,
        'source_connector_onresponse_after_connecttonode': source_connector_onresponse_after_connecttonode,
        'source_peerfinder_requests_peers_after_connector_success': source_peerfinder_requests_peers_after_connector_success,
        'source_registration_happens_before_listener_success': source_registration_happens_before_listener_success,
        'result': 'request_peers_observed_so_followup_connect_reaches_post_registration_success_at_least_transiently'
        if request_peers_count > 0
        and source_connector_onresponse_after_connecttonode
        and source_peerfinder_requests_peers_after_connector_success
        and source_registration_happens_before_listener_success
        else 'request_peers_does_not_yet_pin_followup_connect_past_registration_success',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
