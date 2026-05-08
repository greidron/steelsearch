#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

SRC = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpTransport.java')
OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\] closeNanoTime \[(\d+)\]')


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
        print('usage: check_any_channel_close_listener_owns_whole_nodechannels_cascade.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    src = SRC.read_text(errors='ignore')
    source_has_per_channel_close_listener = 'ch.addCloseListener' in src
    source_listener_calls_nodechannels_close = 'nodeChannels.close();' in src

    groups = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            order = int(m.group(3))
            nano = int(m.group(4))
            groups.setdefault(cid, []).append((order, idx, nano))

    counts = []
    spreads = []
    for cid, rows in groups.items():
        rows = sorted(rows)
        counts.append(len(rows))
        spreads.append((rows[-1][2] - rows[0][2]) / 1_000_000)

    result = 'any_sibling_close_listener_in_tcptransport_owns_the_whole_nodechannels_teardown_cascade' if source_has_per_channel_close_listener and source_listener_calls_nodechannels_close and counts and min(counts) == 13 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'source_has_per_channel_close_listener': source_has_per_channel_close_listener,
        'source_listener_calls_nodechannels_close': source_listener_calls_nodechannels_close,
        'named_rust_connection_count': len(groups),
        'channel_close_count_min': min(counts) if counts else None,
        'channel_close_count_median': median(counts),
        'close_spread_median_ms': median(spreads),
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
