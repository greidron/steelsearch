#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

FIRST_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*serverChannel \[(true|false)\] idleForMs \[(\d+)\] .*closeOrder \[(\d+)\]')
UNKNOWN_HINT_RE = re.compile(r'netty4 tcp channel close completed for \[\[id: [^,]+, L:/127\.0\.0\.1:(\d+) ! R:[^\]]+\]\] with hint \[unknown\]')
INACTIVE_RE = re.compile(r'netty4 message channel handler channelInactive on \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), ')


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_remaining_unknown_is_channelinactive_race.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    text = (Path(artifact['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore')
    lines = text.splitlines()

    low_first_ports = set()
    first_by_conn = {}
    for i, line in enumerate(lines):
        m = FIRST_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            port = int(m.group(3))
            order = int(m.group(6))
            cur = first_by_conn.get(cid)
            if cur is None or order < cur[0]:
                first_by_conn[cid] = (order, idx, port, i)
    for _cid, (_order, idx, port, _i) in first_by_conn.items():
        if idx in (1, 2, 5, 6):
            low_first_ports.add(port)

    unknown_rows = []
    for i, line in enumerate(lines):
        m = UNKNOWN_HINT_RE.search(line)
        if not m:
            continue
        port = int(m.group(1))
        if port not in low_first_ports:
            continue
        inactive_after = None
        for j in range(i + 1, min(i + 20, len(lines))):
            mi = INACTIVE_RE.search(lines[j])
            if mi and int(mi.group(1)) == port:
                inactive_after = j - i
                break
        unknown_rows.append({'port': port, 'hint_line_index': i, 'channelInactive_after_lines': inactive_after})

    race_count = sum(1 for row in unknown_rows if row['channelInactive_after_lines'] is not None)
    result = 'inconclusive'
    if len(unknown_rows) == 1 and race_count == 1:
        result = 'remaining_low_index_unknown_is_best_explained_by_close_trace_before_channelinactive_race_not_by_a_distinct_close_path'

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'low_index_unknown_rows': unknown_rows,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
