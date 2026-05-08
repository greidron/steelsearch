#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def parse_probe_timeout_ms(text: str):
    m = re.search(r'PROBE_HANDSHAKE_TIMEOUT_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', text, re.S)
    return int(m.group(1)) if m else None


def parse_connect_timeout_ms(text: str):
    m = re.search(r'TCP_CONNECT_TIMEOUT.*?new TimeValue\((\d+),\s*TimeUnit\.SECONDS\)', text, re.S)
    return int(m.group(1)) * 1000 if m else None


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_close_window_timeout_scale.py <HandshakingTransportAddressConnector.java> <NetworkService.java> <close_window.json>')

    connector = Path(sys.argv[1]).read_text()
    network = Path(sys.argv[2]).read_text()
    window = json.loads(Path(sys.argv[3]).read_text())

    probe_timeout_ms = parse_probe_timeout_ms(connector)
    connect_timeout_ms = parse_connect_timeout_ms(network)
    max_window_ms = window.get('max_window_ms')

    closer_to_probe_than_connect = (
        probe_timeout_ms is not None and connect_timeout_ms is not None and max_window_ms is not None
        and max_window_ms < probe_timeout_ms
        and max_window_ms * 10 < connect_timeout_ms
    )

    result = (
        'observed_peer_close_window_matches_probe_handshake_timeout_scale_not_transport_connect_timeout_scale'
        if closer_to_probe_than_connect
        else 'close_window_timeout_scale_not_fully_established'
    )

    print(json.dumps({
        'probe_handshake_timeout_ms': probe_timeout_ms,
        'transport_connect_timeout_ms': connect_timeout_ms,
        'max_window_ms': max_window_ms,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
