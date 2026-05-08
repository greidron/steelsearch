#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

FIRST_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')
HINT_RE = re.compile(r'netty4 tcp channel close completed for \[\[id: [^,]+, L:/127\.0\.0\.1:(\d+) ! R:[^\]]+\]\] with hint \[([^\]]+)\]')
LOW = {1, 2, 5, 6}


def summarize(path_str):
    artifact = json.loads(Path(path_str).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    text = stdout_log.read_text(errors='ignore')
    first_by_conn = {}
    for line in text.splitlines():
        m = FIRST_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            port = int(m.group(3))
            order = int(m.group(4))
            cur = first_by_conn.get(cid)
            if cur is None or order < cur[0]:
                first_by_conn[cid] = (order, idx, port)
    hint_by_port = {}
    for line in text.splitlines():
        m = HINT_RE.search(line)
        if m:
            hint_by_port[int(m.group(1))] = m.group(2)
    low = [(cid, idx, port) for cid, (order, idx, port) in first_by_conn.items() if idx in LOW]
    counts = Counter()
    missing = 0
    for _cid, _idx, port in low:
        hint = hint_by_port.get(port)
        if hint is None:
            missing += 1
        else:
            counts[hint] += 1
    return {
        'work_dir': artifact['work_dir'],
        'low_index_first_count_1_2_5_6': len(low),
        'matched_hint_count': sum(counts.values()),
        'missing_hint_count': missing,
        'hint_distribution': dict(sorted(counts.items())),
        'unknown_count': counts.get('unknown', 0),
        'explicit_local_close_count': counts.get('explicitLocalClose', 0),
    }


def main():
    if len(sys.argv) != 3:
        print('usage: check_explicit_local_close_hint_reduces_unknown.py <before.json> <after.json>', file=sys.stderr)
        return 2
    before = summarize(sys.argv[1])
    after = summarize(sys.argv[2])
    reduced = after['unknown_count'] < before['unknown_count']
    explicit = after['explicit_local_close_count'] > 0
    result = 'explicit_local_close_hint_reduces_unknown_for_low_index_first_close' if reduced and explicit else 'inconclusive'
    print(json.dumps({
        'before': before,
        'after': after,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
