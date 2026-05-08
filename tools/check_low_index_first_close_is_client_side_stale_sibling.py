#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
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
        print('usage: check_low_index_first_close_is_client_side_stale_sibling.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
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
    result = 'low_index_first_close_is_a_client_side_stale_sibling' if low and all(x['server'] is False for x in low) and median([x['idle'] for x in low]) >= 500 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'first_close_count': len(first),
        'low_index_first_count_1_2_5_6': len(low),
        'low_index_first_server_false_count': sum(x['server'] is False for x in low),
        'low_index_first_idle_median_ms': median([x['idle'] for x in low]),
        'low_index_first_idle_min_ms': min((x['idle'] for x in low), default=None),
        'low_index_first_idle_max_ms': max((x['idle'] for x in low), default=None),
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
