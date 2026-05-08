#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERN = re.compile(r'^\[(?P<ts>[^\]]+)\].*node connection \[(?P<cid>\d+)\] observed close on channelIndex \[(?P<idx>\d+)\]')


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_actual_close_ordering_first_channel_distribution.py <TcpTransport.java> <stdout.log>', file=sys.stderr)
        return 2

    tcp_source = Path(sys.argv[1]).read_text()
    lines = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace').splitlines()

    source_handshake_is_channel_zero = 'final TcpChannel handshakeChannel = channels.get(0);' in tcp_source

    by_connection = {}
    for line in lines:
        m = PATTERN.search(line)
        if not m:
            continue
        cid = int(m.group('cid'))
        idx = int(m.group('idx'))
        ts = m.group('ts')
        by_connection.setdefault(cid, []).append((ts, idx))

    first_index_counts = {}
    ambiguous_same_ts_count = 0
    for items in by_connection.values():
        items.sort()
        first_ts = items[0][0]
        first_indices = sorted({idx for ts, idx in items if ts == first_ts})
        if len(first_indices) == 1:
            first_index_counts[first_indices[0]] = first_index_counts.get(first_indices[0], 0) + 1
        else:
            ambiguous_same_ts_count += 1

    dominant_first_index = None
    dominant_first_index_count = 0
    if first_index_counts:
        dominant_first_index, dominant_first_index_count = max(first_index_counts.items(), key=lambda kv: kv[1])

    result = 'actual_close_ordering_distribution_inconclusive'
    if source_handshake_is_channel_zero and dominant_first_index == 0 and dominant_first_index_count > 0:
        result = 'actual_close_ordering_shows_channel_zero_as_the_dominant_unique_first_close_index_while_many_connections_remain_same_timestamp_ambiguous'

    print(json.dumps({
        'source_handshake_is_channel_zero': source_handshake_is_channel_zero,
        'connection_count': len(by_connection),
        'ambiguous_same_ts_count': ambiguous_same_ts_count,
        'first_index_counts': first_index_counts,
        'dominant_first_index': dominant_first_index,
        'dominant_first_index_count': dominant_first_index_count,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
