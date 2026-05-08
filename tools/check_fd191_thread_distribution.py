#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HEADER_RE = re.compile(
    r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+(?P<event>syscalls:sys_enter_[^:]+):\s*(?P<rest>.*)$'
)
FD_RE = re.compile(r'fd:\s+0x(?P<fd>[0-9a-fA-F]+)')


def main() -> int:
    path = Path(sys.argv[1])
    target_fd = int(sys.argv[2])
    per_tid = defaultdict(lambda: {'comm': None, 'target_fd_reads': 0, 'epoll_pwait': 0, 'epoll_pwait2': 0, 'all_reads': 0})
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = HEADER_RE.match(line)
        if not m:
            continue
        tid = int(m.group('tid'))
        event = m.group('event').split('sys_enter_', 1)[1]
        rest = m.group('rest')
        bucket = per_tid[tid]
        bucket['comm'] = m.group('comm').strip()
        if event == 'read':
            bucket['all_reads'] += 1
            fdm = FD_RE.search(rest)
            if fdm and int(fdm.group('fd'), 16) == target_fd:
                bucket['target_fd_reads'] += 1
        elif event in ('epoll_pwait', 'epoll_pwait2'):
            bucket[event] += 1

    overlap = []
    read_only = []
    for tid, row in sorted(per_tid.items()):
        if row['target_fd_reads'] == 0:
            continue
        out = {'tid': tid, **row}
        has_wait = row['epoll_pwait'] > 0 or row['epoll_pwait2'] > 0
        if has_wait:
            overlap.append(out)
        else:
            read_only.append(out)

    overlap_total = sum(r['target_fd_reads'] for r in overlap)
    read_only_total = sum(r['target_fd_reads'] for r in read_only)

    result = {
        'path': str(path),
        'target_fd': target_fd,
        'overlap_threads': overlap,
        'read_only_threads': read_only,
        'overlap_total_reads': overlap_total,
        'read_only_total_reads': read_only_total,
        'checker_result': (
            'fd191_payload_path_is_mainly_read_only_thread_path_with_only_occasional_overlap_thread_reads'
            if read_only_total > overlap_total else
            'fd191_payload_path_is_not_dominated_by_read_only_threads'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
