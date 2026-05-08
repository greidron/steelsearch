#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLOSE_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*closeOrder \[(\d+)\]')
HINT_RE = re.compile(r'netty4 tcp channel close completed for \[\[id: [^,]+, L:/127\.0\.0\.1:(\d+) ! R:[^\]]+\]\] with hint \[([^\]]+)\]')
INACTIVE_RE = re.compile(r'netty4 message channel handler channelInactive on \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), ')
LOW = {1, 2, 5, 6}


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_non_low_index_unknowns_are_mostly_race_with_one_residue.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    lines = (Path(artifact['work_dir']) / 'opensearch' / 'stdout.log').read_text(errors='ignore').splitlines()

    close_by_port = {}
    for i, line in enumerate(lines):
        m = CLOSE_RE.search(line)
        if m:
            close_by_port[int(m.group(3))] = {
                'connection_id': int(m.group(1)),
                'index': int(m.group(2)),
                'close_order': int(m.group(4)),
                'close_line_index': i,
            }

    rows = []
    for i, line in enumerate(lines):
        m = HINT_RE.search(line)
        if not m or m.group(2) != 'unknown':
            continue
        port = int(m.group(1))
        meta = close_by_port.get(port)
        if not meta or meta['index'] in LOW:
            continue
        inactive_after = None
        for j in range(i + 1, min(i + 50, len(lines))):
            mi = INACTIVE_RE.search(lines[j])
            if mi and int(mi.group(1)) == port:
                inactive_after = j - i
                break
        rows.append({
            'port': port,
            'connection_id': meta['connection_id'],
            'index': meta['index'],
            'close_order': meta['close_order'],
            'channelInactive_after_lines': inactive_after,
        })

    race_rows = [row for row in rows if row['channelInactive_after_lines'] is not None]
    residue_rows = [row for row in rows if row['channelInactive_after_lines'] is None]

    result = 'inconclusive'
    if len(rows) == 10 and len(race_rows) == 9 and len(residue_rows) == 1:
        result = 'non_low_index_unknowns_are_mostly_channelinactive_ordering_race_with_one_remaining_residue'

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'non_low_index_unknown_count': len(rows),
        'race_count': len(race_rows),
        'residue_count': len(residue_rows),
        'residue_rows': residue_rows,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
