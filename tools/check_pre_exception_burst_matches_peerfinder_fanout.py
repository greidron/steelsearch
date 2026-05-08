#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_pre_exception_burst_matches_peerfinder_fanout.py <PeerFinder.java> <pre_exception_sequence.json>')

    source = Path(sys.argv[1]).read_text()
    seq = load(sys.argv[2])

    source_peerfinder_fanout = (
        'response.getClusterManagerNode().map(DiscoveryNode::getAddress).ifPresent(PeerFinder.this::startProbe);' in source
        and 'response.getKnownPeers().stream().map(DiscoveryNode::getAddress).forEach(PeerFinder.this::startProbe);' in source
        and 'peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer);' in source
    )

    sequence = seq.get('sequence') or []
    request_peers = [e for e in sequence if e.get('first_action') == 'internal:discovery/request_peers']
    tcp = [e for e in sequence if e.get('first_action') == 'internal:tcp/handshake']
    same_ms_burst = len({e.get('connection_started_at_ms') for e in request_peers}) == 1 if request_peers else False

    result = (
        'pre_exception_request_peers_burst_is_consistent_with_peerfinder_fanout_round'
        if source_peerfinder_fanout and len(request_peers) >= 3 and len(tcp) >= 1 and same_ms_burst
        else 'pre_exception_burst_not_fully_matched_to_peerfinder_fanout'
    )

    print(json.dumps({
        'source_peerfinder_fanout': source_peerfinder_fanout,
        'request_peers_count': len(request_peers),
        'tcp_handshake_count': len(tcp),
        'request_peers_same_ms_burst': same_ms_burst,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
