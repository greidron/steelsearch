#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*serverChannel \[(true|false)\] idleForMs \[(\d+)\] closeOrder \[(\d+)\]')


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    if n % 2:
        return xs[n // 2]
    return (xs[n // 2 - 1] + xs[n // 2]) / 2


def main():
    if len(sys.argv) != 2:
        print('usage: check_stale_sibling_band_points_to_java_client_side_close.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    work_dir = Path(artifact['work_dir'])
    stdout_log = work_dir / 'opensearch' / 'stdout.log'
    capture_path = work_dir / 'steelsearch' / 'data' / 'transport-seed-capture.json'

    rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            server = m.group(3) == 'true'
            idle = int(m.group(4))
            order = int(m.group(5))
            rows.setdefault(cid, []).append((order, idx, server, idle))

    first = []
    for cid, vals in rows.items():
        order, idx, server, idle = sorted(vals)[0]
        first.append({'connection_id': cid, 'idx': idx, 'server': server, 'idle': idle})

    low = [x for x in first if x['idx'] in (1, 2, 5, 6)]

    capture = json.loads(capture_path.read_text())
    entries = capture if isinstance(capture, list) else capture.get('connections', [])
    target = [c for c in entries if (c.get('first_frame') or {}).get('action_hint') in (
        'internal:cluster/request_pre_vote',
        'internal:cluster/coordination/start_join',
        'internal:cluster/coordination/publish_state',
        'internal:coordination/fault_detection/follower_check',
    )]
    remote_eof_count = sum(c.get('connection_end') == 'remote_eof' for c in target)
    result = '600_800ms_stale_sibling_band_points_more_directly_to_java_client_side_close_than_to_rust_peer_half_close' if low and all(x['server'] is False for x in low) and median([x['idle'] for x in low]) >= 600 and target and remote_eof_count == len(target) else 'inconclusive'
    print(json.dumps({
        'work_dir': str(work_dir),
        'low_index_first_count_1_2_5_6': len(low),
        'low_index_first_server_false_count': sum(x['server'] is False for x in low),
        'low_index_first_idle_median_ms': median([x['idle'] for x in low]),
        'target_action_connection_count': len(target),
        'target_action_remote_eof_count': remote_eof_count,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
