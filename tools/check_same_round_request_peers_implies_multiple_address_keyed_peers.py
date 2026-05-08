#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_same_round_request_peers_implies_multiple_address_keyed_peers.py <PeerFinder.java> <exception_round_role.json>')

    source = Path(sys.argv[1]).read_text()
    role = load(sys.argv[2])

    source_uses_address_keyed_peers = (
        'private final Map<TransportAddress, Peer> peersByAddress = new LinkedHashMap<>();' in source
        and 'peersByAddress.values().removeIf(Peer::handleWakeUp);' in source
    )
    source_wakeup_requests_peers_per_connected_peer = (
        'if (transportService.nodeConnected(discoveryNode)) {' in source
        and 'if (peersRequestInFlight == false) {' in source
        and 'requestPeers();' in source
    )

    same_round_request_peers_count = role.get('same_round_request_peers_count', 0)
    artifact_shows_multi_request_peers_burst = same_round_request_peers_count >= 3

    result = (
        'same_round_request_peers_burst_implies_multiple_address_keyed_connected_peer_entries_not_multiple_seed_candidates'
        if source_uses_address_keyed_peers and source_wakeup_requests_peers_per_connected_peer and artifact_shows_multi_request_peers_burst
        else 'same_round_request_peers_burst_not_fully_explained'
    )

    print(json.dumps({
        'source_uses_address_keyed_peers': source_uses_address_keyed_peers,
        'source_wakeup_requests_peers_per_connected_peer': source_wakeup_requests_peers_per_connected_peer,
        'same_round_request_peers_count': same_round_request_peers_count,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
