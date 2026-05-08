#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'node connection \[(?P<cid>\d+)\] observed close on channelIndex \[(?P<idx>\d+)\].*closeOrder \[(?P<order>\d+)\]')


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_finer_ordering_first_channel_distribution.py <stdout.log>', file=sys.stderr)
        return 2
    by = {}
    for line in Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines():
        m = PATTERN.search(line)
        if not m:
            continue
        cid = int(m.group('cid'))
        idx = int(m.group('idx'))
        order = int(m.group('order'))
        by.setdefault(cid, []).append((order, idx))
    first_counts = {}
    for items in by.values():
        items.sort()
        first_idx = items[0][1]
        first_counts[first_idx] = first_counts.get(first_idx, 0) + 1
    dominant_first_index = None
    dominant_first_index_count = 0
    if first_counts:
        dominant_first_index, dominant_first_index_count = max(first_counts.items(), key=lambda kv: kv[1])
    result = 'finer_ordering_first_channel_distribution_extracted'
    print(json.dumps({
        'connection_count': len(by),
        'first_index_counts': first_counts,
        'dominant_first_index': dominant_first_index,
        'dominant_first_index_count': dominant_first_index_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
