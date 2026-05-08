#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'node connection \[(?P<cid>\d+)\] observed close on channelIndex \[(?P<idx>\d+)\].*closeOrder \[(?P<order>\d+)\]')
COUNT_RE = {
    'BULK': re.compile(r'CONNECTIONS_PER_NODE_BULK\s*=\s*intSetting\([^\n]*\n\s*"transport\.connections_per_node\.bulk",\n\s*(?P<count>\d+),'),
    'PING': re.compile(r'CONNECTIONS_PER_NODE_PING\s*=\s*intSetting\([^\n]*\n\s*"transport\.connections_per_node\.ping",\n\s*(?P<count>\d+),'),
    'STATE': re.compile(r'CONNECTIONS_PER_NODE_STATE\s*=\s*intSetting\([^\n]*\n\s*"transport\.connections_per_node\.state",\n\s*(?P<count>\d+),'),
    'RECOVERY': re.compile(r'CONNECTIONS_PER_NODE_RECOVERY\s*=\s*intSetting\([^\n]*\n\s*"transport\.connections_per_node\.recovery",\n\s*(?P<count>\d+),'),
    'REG': re.compile(r'CONNECTIONS_PER_NODE_REG\s*=\s*intSetting\([^\n]*\n\s*"transport\.connections_per_node\.reg",\n\s*(?P<count>\d+),'),
}


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_first_close_indices_vs_profile_classes.py <TransportSettings.java> <stdout.log>', file=sys.stderr)
        return 2

    settings_src = Path(sys.argv[1]).read_text()
    counts = {}
    for key, regex in COUNT_RE.items():
        m = regex.search(settings_src)
        if not m:
            print(f'missing count for {key}', file=sys.stderr)
            return 1
        counts[key] = int(m.group('count'))

    ranges = {}
    offset = 0
    for key in ['BULK', 'PING', 'STATE', 'RECOVERY', 'REG']:
        ranges[key] = list(range(offset, offset + counts[key]))
        offset += counts[key]

    by = {}
    for line in Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace').splitlines():
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
        idx = items[0][1]
        first_counts[idx] = first_counts.get(idx, 0) + 1

    class_counts = {k: 0 for k in ranges}
    index_to_class = {}
    for cls, indices in ranges.items():
        for idx in indices:
            index_to_class[idx] = cls
    for idx, count in first_counts.items():
        cls = index_to_class.get(idx)
        if cls:
            class_counts[cls] += count

    result = 'first_close_indices_mapped_to_default_profile_classes'
    print(json.dumps({
        'default_profile_ranges': ranges,
        'first_index_counts': first_counts,
        'first_class_counts': class_counts,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
