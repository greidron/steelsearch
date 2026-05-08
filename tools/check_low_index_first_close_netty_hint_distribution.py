#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

FIRST_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')
HINT_RE = re.compile(r'netty4 tcp channel close completed for \[\[id: [^,]+, L:/127\.0\.0\.1:(\d+) ! R:[^\]]+\]\] with hint \[([^\]]+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_low_index_first_close_netty_hint_distribution.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
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
            port = int(m.group(1))
            hint = m.group(2)
            hint_by_port[port] = hint

    low = [(cid, idx, port) for cid, (order, idx, port) in first_by_conn.items() if idx in (1,2,5,6)]
    hint_counts = Counter()
    missing = 0
    for cid, idx, port in low:
        hint = hint_by_port.get(port)
        if hint is None:
            missing += 1
        else:
            hint_counts[hint] += 1
    result = 'low_index_first_close_is_mostly_bound_to_netty_hint_unknown_not_exception_or_channelinactive' if hint_counts and hint_counts.get('unknown', 0) >= sum(hint_counts.values()) - 1 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'low_index_first_count_1_2_5_6': len(low),
        'matched_netty_hint_count': sum(hint_counts.values()),
        'missing_netty_hint_count': missing,
        'netty_hint_distribution': dict(sorted(hint_counts.items())),
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
