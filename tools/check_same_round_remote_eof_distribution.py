#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_same_round_remote_eof_distribution.py <report.json> <start_ms> <tolerance_ms>')

    report = json.loads(Path(sys.argv[1]).read_text())
    start_ms = int(sys.argv[2])
    tolerance_ms = int(sys.argv[3])
    capture = report.get('steelsearch_transport_capture') or []

    same_round = [
        e for e in capture
        if e.get('connection_started_at_ms') is not None
        and abs(e.get('connection_started_at_ms') - start_ms) <= tolerance_ms
    ]

    remote_eof_count = sum(1 for e in same_round if e.get('first_post_response_event') == 'remote_eof')
    direct_full_connect_count = sum(1 for e in same_round if (e.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake')

    result = (
        'all_same_round_members_get_remote_eof_so_exception_is_branch_specific_not_eof_specific'
        if same_round and remote_eof_count == len(same_round) and direct_full_connect_count == 1
        else 'same_round_remote_eof_distribution_not_fully_established'
    )

    print(json.dumps({
        'same_round_count': len(same_round),
        'remote_eof_count': remote_eof_count,
        'direct_full_connect_count': direct_full_connect_count,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
