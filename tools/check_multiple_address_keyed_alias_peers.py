#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_multiple_address_keyed_alias_peers.py <PeerFinder.java> <exception_round_role.json> <report.json>')

    source = Path(sys.argv[1]).read_text()
    role = load(sys.argv[2])
    report = load(sys.argv[3])

    source_keys_peers_by_probe_address = (
        'private final Map<TransportAddress, Peer> peersByAddress = new LinkedHashMap<>();' in source
        and 'peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer);' in source
        and 'discoveryNode.set(remoteNode);' in source
        and 'peersByAddress.remove(transportAddress, Peer.this);' in source
    )
    source_does_not_rekey_to_canonical_remote_address = (
        'discoveryNode.set(remoteNode);' in source
        and 'peersByAddress.put(remoteNode.getAddress()' not in source
    )

    same_round_request_peers_count = role.get('same_round_request_peers_count', 0)
    artifact_has_multiple_address_keyed_entries = same_round_request_peers_count >= 3

    seed_peer_identity = report.get('seed_peer_identity') or {}
    canonical_remote_transport_address = (seed_peer_identity.get('discovery_node') or {}).get('transport_address')
    artifact_has_single_canonical_remote_identity = bool(canonical_remote_transport_address)

    result = (
        'multiple_address_keyed_peer_entries_can_persist_as_aliases_of_single_canonical_remote_node'
        if source_keys_peers_by_probe_address
        and source_does_not_rekey_to_canonical_remote_address
        and artifact_has_multiple_address_keyed_entries
        and artifact_has_single_canonical_remote_identity
        else 'multiple_address_keyed_alias_peers_not_fully_established'
    )

    print(json.dumps({
        'source_keys_peers_by_probe_address': source_keys_peers_by_probe_address,
        'source_does_not_rekey_to_canonical_remote_address': source_does_not_rekey_to_canonical_remote_address,
        'same_round_request_peers_count': same_round_request_peers_count,
        'canonical_remote_transport_address': canonical_remote_transport_address,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
