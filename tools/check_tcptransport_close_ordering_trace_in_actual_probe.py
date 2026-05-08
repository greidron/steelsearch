#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'node connection \[(?P<connection_id>\d+)\] observed close on channelIndex \[(?P<channel_index>\d+)\] channel \[(?P<channel>.*)\] for \[(?P<node>.*)\]')


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_tcptransport_close_ordering_trace_in_actual_probe.py <stdout.log>', file=sys.stderr)
        return 2
    lines = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines()
    matches = []
    for line in lines:
        m = PATTERN.search(line)
        if m:
            matches.append(m.groupdict())
    unique_connection_ids = sorted({m['connection_id'] for m in matches})
    unique_channel_indices = sorted({int(m['channel_index']) for m in matches})
    result = 'tcptransport_close_ordering_trace_not_observed'
    if matches:
        result = 'tcptransport_close_ordering_trace_observed_in_actual_probe'
    print(json.dumps({
        'close_trace_count': len(matches),
        'unique_connection_id_count': len(unique_connection_ids),
        'unique_channel_indices': unique_channel_indices,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
