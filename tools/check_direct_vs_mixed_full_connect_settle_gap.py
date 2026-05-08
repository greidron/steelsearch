#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_direct_vs_mixed_full_connect_settle_gap.py <direct_tracer_check.json> <mixed_full_connect_check.json>'}))
        return 1
    direct = load(sys.argv[1])
    mixed = load(sys.argv[2])

    direct_settled = int(direct.get('publish_state_count', 0)) > 0 and int(direct.get('commit_state_count', 0)) > 0
    mixed_retrying = mixed.get('result') == 'full_connect_is_retried_repeatedly_but_never_settles_into_connected_nodes_reuse'

    if direct_settled and mixed_retrying:
        result = 'direct_reference_settles_after_handshake_while_mixed_retries_full_connect_without_settling'
    elif direct_settled:
        result = 'direct_reference_settles_but_mixed_gap_not_reproduced'
    else:
        result = 'direct_reference_not_sufficient'

    print(json.dumps({
        'direct_publish_state_count': int(direct.get('publish_state_count', 0)),
        'direct_commit_state_count': int(direct.get('commit_state_count', 0)),
        'mixed_transport_handshake_first_frame_count': int(mixed.get('transport_handshake_first_frame_count', 0)),
        'mixed_result': mixed.get('result'),
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
