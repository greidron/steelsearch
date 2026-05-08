#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit('usage: check_pre_exception_request_peers_burst.py <pre_exception_sequence.json>')

    seq = load(sys.argv[1]).get('sequence') or []
    request_peers = [e for e in seq if e.get('first_action') == 'internal:discovery/request_peers']
    tcp = [e for e in seq if e.get('first_action') == 'internal:tcp/handshake']

    same_ms_burst = len({e.get('connection_started_at_ms') for e in request_peers}) == 1 if request_peers else False
    result = (
        'exception_path_is_preceded_by_request_peers_burst_with_concurrent_tcp_handshake'
        if len(request_peers) >= 3 and len(tcp) >= 1 and same_ms_burst
        else 'pre_exception_request_peers_burst_not_fully_established'
    )

    print(json.dumps({
        'request_peers_count': len(request_peers),
        'tcp_handshake_count': len(tcp),
        'request_peers_same_ms_burst': same_ms_burst,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
