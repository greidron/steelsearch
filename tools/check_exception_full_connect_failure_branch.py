#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_exception_full_connect_failure_branch.py <PeerFinder.java> <exception_round_role.json>')

    source = Path(sys.argv[1]).read_text()
    role = load(sys.argv[2])

    source_has_connecting_peer_failure_remove = (
        'transportAddressConnector.connectToRemoteMasterNode' in source
        and 'peersByAddress.remove(transportAddress, Peer.this);' in source
    )
    source_request_peers_failure_only_clears_inflight = (
        'peersRequestInFlight = false;' in source
        and 'logger.debug(new ParameterizedMessage("{} peers request failed", Peer.this), exp);' in source
    )
    artifact_has_unique_full_connect_member = role.get('same_round_direct_full_connect_count') == 1 and role.get('same_round_request_peers_count', 0) >= 3

    result = (
        'exception_member_is_only_round_member_on_connecting_peer_failure_remove_branch'
        if source_has_connecting_peer_failure_remove and source_request_peers_failure_only_clears_inflight and artifact_has_unique_full_connect_member
        else 'exception_full_connect_failure_branch_not_fully_established'
    )

    print(json.dumps({
        'source_has_connecting_peer_failure_remove': source_has_connecting_peer_failure_remove,
        'source_request_peers_failure_only_clears_inflight': source_request_peers_failure_only_clears_inflight,
        'artifact_has_unique_full_connect_member': artifact_has_unique_full_connect_member,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
