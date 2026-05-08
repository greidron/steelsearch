#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_alias_entries_not_from_request_peers_response.py <PeerFinder.java> <report.json> <start_ms>')

    source = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())
    start_ms = int(sys.argv[3])
    capture = report.get('steelsearch_transport_capture') or []

    source_request_peers_response_can_only_start_probes_from_response_nodes = (
        'response.getClusterManagerNode().map(DiscoveryNode::getAddress).ifPresent(PeerFinder.this::startProbe);' in source
        and 'response.getKnownPeers().stream().map(DiscoveryNode::getAddress).forEach(PeerFinder.this::startProbe);' in source
    )

    same_round_request_peers = [
        e for e in capture
        if e.get('connection_started_at_ms') is not None
        and abs(e.get('connection_started_at_ms') - start_ms) <= 1
        and (e.get('first_frame') or {}).get('action_hint') == 'internal:discovery/request_peers'
    ]

    response_message_lengths = sorted({(e.get('response_frame') or {}).get('message_length') for e in same_round_request_peers})
    all_minimal_emptyish = bool(same_round_request_peers) and response_message_lengths == [29]

    result = (
        'same_round_alias_entries_are_not_explained_by_request_peers_responses_so_remaining_sources_are_cluster_state_or_configured_hosts'
        if source_request_peers_response_can_only_start_probes_from_response_nodes and all_minimal_emptyish
        else 'alias_entry_source_not_yet_reduced_past_request_peers_responses'
    )

    print(json.dumps({
        'source_request_peers_response_can_only_start_probes_from_response_nodes': source_request_peers_response_can_only_start_probes_from_response_nodes,
        'same_round_request_peers_count': len(same_round_request_peers),
        'response_message_lengths': response_message_lengths,
        'all_minimal_emptyish': all_minimal_emptyish,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
