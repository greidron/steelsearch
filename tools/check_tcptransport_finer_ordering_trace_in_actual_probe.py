#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'node connection \[(?P<connection_id>\d+)\] observed close on channelIndex \[(?P<channel_index>\d+)\] channel \[(?P<channel>.*)\] for \[(?P<node>.*)\] closeOrder \[(?P<close_order>\d+)\] closeNanoTime \[(?P<close_nano>\d+)\]')


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_tcptransport_finer_ordering_trace_in_actual_probe.py <stdout.log>', file=sys.stderr)
        return 2
    lines = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace').splitlines()
    matches = []
    for line in lines:
        m = PATTERN.search(line)
        if m:
            matches.append(m.groupdict())
    result = 'tcptransport_finer_ordering_trace_not_observed'
    if matches:
        result = 'tcptransport_finer_ordering_trace_observed_in_actual_probe'
    print(json.dumps({
        'close_trace_count': len(matches),
        'has_close_order': bool(matches),
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
