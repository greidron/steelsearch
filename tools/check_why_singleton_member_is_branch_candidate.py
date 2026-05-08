#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_why_singleton_member_is_branch_candidate.py <PeerFinder.java> <exception_round_role.json>')

    source = Path(sys.argv[1]).read_text()
    role = load(sys.argv[2])

    source_has_probe_to_connecting_peer_path = (
        'peersByAddress.computeIfAbsent(transportAddress, this::createConnectingPeer);' in source
        and 'peer.establishConnection();' in source
        and 'transportAddressConnector.connectToRemoteMasterNode' in source
    )
    source_has_connected_peer_request_peers_path = (
        'if (transportService.nodeConnected(discoveryNode)) {' in source
        and 'if (peersRequestInFlight == false) {' in source
        and 'requestPeers();' in source
    )
    artifact_has_singleton_direct_full_connect_member = (
        role.get('same_round_direct_full_connect_count') == 1
        and role.get('same_round_request_peers_count', 0) >= 3
        and role.get('same_round_tcp_count', 0) >= 1
    )

    result = (
        'singleton_member_is_branch_candidate_because_only_it_is_on_probe_to_full_connect_path_while_others_are_request_peers_members'
        if source_has_probe_to_connecting_peer_path
        and source_has_connected_peer_request_peers_path
        and artifact_has_singleton_direct_full_connect_member
        else 'singleton_branch_candidate_reason_not_fully_established'
    )

    print(json.dumps({
        'source_has_probe_to_connecting_peer_path': source_has_probe_to_connecting_peer_path,
        'source_has_connected_peer_request_peers_path': source_has_connected_peer_request_peers_path,
        'artifact_has_singleton_direct_full_connect_member': artifact_has_singleton_direct_full_connect_member,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
