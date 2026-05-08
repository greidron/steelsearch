#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_true_idle_pair_skew_is_not_explained_by_simple_open_order.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            order = int(m.group(3))
            rows.setdefault(cid, []).append((order, idx))
    first = Counter(sorted(v)[0][1] for v in rows.values())
    bulk_pair = {'1': first[1], '2': first[2]}
    recovery_pair = {'5': first[5], '6': first[6]}
    simple_lower_first = bulk_pair['1'] > bulk_pair['2'] and recovery_pair['5'] > recovery_pair['6']
    simple_higher_first = bulk_pair['1'] < bulk_pair['2'] and recovery_pair['5'] < recovery_pair['6']
    result = 'true_idle_pair_skew_is_not_explained_by_a_single_monotonic_open_order_rule_and_leans_toward_peer_detail' if not simple_lower_first and not simple_higher_first else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'bulk_idle_pair_first_close_counts': bulk_pair,
        'recovery_idle_pair_first_close_counts': recovery_pair,
        'simple_lower_first_rule_holds': simple_lower_first,
        'simple_higher_first_rule_holds': simple_higher_first,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
