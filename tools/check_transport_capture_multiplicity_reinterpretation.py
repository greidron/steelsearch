#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_transport_capture_multiplicity_reinterpretation.py <old_round_role.json> <trace_direct_multiplicity.json>')

    old_role = load(sys.argv[1])
    trace = load(sys.argv[2])

    old_request_peers_burst_present = old_role.get('same_round_request_peers_count', 0) >= 3
    trace_shows_single_requesting_peer_address = trace.get('requesting_peers_addresses') == ['127.0.0.1:57743']
    trace_shows_single_attempting_address = trace.get('attempting_connection_addresses') == ['127.0.0.1:57743']

    result = (
        'old_transport_capture_request_peers_burst_is_better_explained_as_repeated_one_shot_sockets_from_single_peer_than_as_multi_address_peer_multiplicity'
        if old_request_peers_burst_present and trace_shows_single_requesting_peer_address and trace_shows_single_attempting_address
        else 'transport_capture_multiplicity_reinterpretation_not_fully_established'
    )

    print(json.dumps({
        'old_request_peers_burst_present': old_request_peers_burst_present,
        'trace_shows_single_requesting_peer_address': trace_shows_single_requesting_peer_address,
        'trace_shows_single_attempting_address': trace_shows_single_attempting_address,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
