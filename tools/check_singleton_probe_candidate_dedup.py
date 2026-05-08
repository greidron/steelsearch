#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_singleton_probe_candidate_dedup.py <PeerFinder.java> <pre_exception_sequence.json>')

    source = Path(sys.argv[1]).read_text()
    seq = load(sys.argv[2])
    entries = seq.get('sequence') or []

    source_dedups_probe_candidates_by_address = (
        'peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer);' in source
        and 'private Peer createConnectingPeer(TransportAddress transportAddress)' in source
    )

    request_peers_count = sum(1 for e in entries if e.get('first_action') == 'internal:discovery/request_peers')
    tcp_handshake_count = sum(1 for e in entries if e.get('first_action') == 'internal:tcp/handshake')
    transport_handshake_followups = sum(1 for e in entries if e.get('follow_up_action') == 'internal:transport/handshake')

    artifact_shows_many_round_triggers_but_one_connecting_candidate = (
        request_peers_count >= 3
        and tcp_handshake_count >= 2
        and transport_handshake_followups == 1
    )

    result = (
        'same_round_multiple_probe_triggers_collapse_to_single_connecting_peer_candidate_via_peersByAddress_dedup'
        if source_dedups_probe_candidates_by_address and artifact_shows_many_round_triggers_but_one_connecting_candidate
        else 'singleton_probe_candidate_dedup_not_fully_established'
    )

    print(json.dumps({
        'source_dedups_probe_candidates_by_address': source_dedups_probe_candidates_by_address,
        'request_peers_count': request_peers_count,
        'tcp_handshake_count': tcp_handshake_count,
        'transport_handshake_followups': transport_handshake_followups,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
