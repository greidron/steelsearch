#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeNanoTime \[(\d+)\]')
DEBUG_RE = re.compile(r'closed transport connection \[(\d+)\] to \[\{rust-replica-1\}.*age \[(\d+)ms\]')


def median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    if n % 2:
        return xs[n//2]
    return (xs[n//2-1] + xs[n//2]) / 2


def main():
    if len(sys.argv) != 2:
        print('usage: check_state_channel_close_is_part_of_connection_level_sibling_teardown.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    groups = {}
    close_age = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            nano = int(m.group(3))
            groups.setdefault(cid, []).append((idx, nano))
            continue
        m = DEBUG_RE.search(line)
        if m:
            close_age[int(m.group(1))] = int(m.group(2))

    named = []
    for cid, rows in sorted(groups.items()):
        idxs = {idx for idx, _ in rows}
        nanos = [nano for _, nano in rows]
        named.append({
            'connection_id': cid,
            'indices': sorted(idxs),
            'channel_count': len(idxs),
            'has_state_4': 4 in idxs,
            'has_ping_3': 3 in idxs,
            'has_any_reg_7_12': any(7 <= i <= 12 for i in idxs),
            'close_spread_ms': (max(nanos) - min(nanos)) / 1_000_000 if nanos else 0,
            'age_ms': close_age.get(cid),
        })

    state_groups = [g for g in named if g['has_state_4']]
    full_sibling_groups = [g for g in state_groups if g['has_ping_3'] and g['has_any_reg_7_12'] and g['channel_count'] >= 10]
    result = 'state_channel_close_is_part_of_connection_level_sibling_teardown_not_a_state_only_inactivity_close' if state_groups and len(full_sibling_groups) == len(state_groups) else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'named_rust_connection_count': len(named),
        'state_channel_group_count': len(state_groups),
        'state_groups_with_ping_and_reg_and_10plus_channels': len(full_sibling_groups),
        'state_group_channel_count_median': median([g['channel_count'] for g in state_groups]),
        'state_group_close_spread_median_ms': median([g['close_spread_ms'] for g in state_groups]),
        'sample_first_three': state_groups[:3],
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
