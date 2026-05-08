#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def parse_millis(pattern: str, text: str):
    m = re.search(pattern, text, re.S)
    return int(m.group(1)) if m else None


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit(
            'usage: check_discovery_scheduler_scale_candidate.py <HandshakingTransportAddressConnector.java> <PeerFinder.java> <close_window.json>'
        )

    connector = Path(sys.argv[1]).read_text()
    peer_finder = Path(sys.argv[2]).read_text()
    window = load(sys.argv[3])

    probe_handshake_timeout_ms = parse_millis(
        r'PROBE_HANDSHAKE_TIMEOUT_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', connector
    )
    find_peers_interval_ms = parse_millis(
        r'DISCOVERY_FIND_PEERS_INTERVAL_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', peer_finder
    )
    request_peers_timeout_ms = parse_millis(
        r'DISCOVERY_REQUEST_PEERS_TIMEOUT_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', peer_finder
    )

    source_has_1s_probe_and_find_peers = (
        probe_handshake_timeout_ms == 1000 and find_peers_interval_ms == 1000
    )
    observed_window_matches_1s_scale = (
        window.get('all_sub_threshold') is True and window.get('max_window_ms') is not None and window.get('max_window_ms') < 1000
    )

    result = (
        'discovery_scheduler_1s_scale_is_more_plausible_next_candidate_than_transport_connect_timeout_scale'
        if source_has_1s_probe_and_find_peers and observed_window_matches_1s_scale and request_peers_timeout_ms == 3000
        else 'discovery_scheduler_scale_candidate_not_fully_established'
    )

    print(json.dumps({
        'probe_handshake_timeout_ms': probe_handshake_timeout_ms,
        'find_peers_interval_ms': find_peers_interval_ms,
        'request_peers_timeout_ms': request_peers_timeout_ms,
        'observed_max_window_ms': window.get('max_window_ms'),
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
