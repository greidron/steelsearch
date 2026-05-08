#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HEADER_RE = re.compile(
    r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+(?P<event>syscalls:sys_enter_[^:]+):'
)


def main() -> int:
    path = Path(sys.argv[1])
    per_tid = defaultdict(lambda: {'comm': None, 'read': 0, 'close': 0, 'epoll_pwait': 0, 'epoll_pwait2': 0})
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = HEADER_RE.match(line)
        if not m:
            continue
        tid = int(m.group('tid'))
        comm = m.group('comm').strip()
        event = m.group('event').split('sys_enter_', 1)[1]
        bucket = per_tid[tid]
        bucket['comm'] = comm
        if event in bucket:
            bucket[event] += 1

    overlap = []
    wait_only = []
    read_only = []
    for tid, counts in sorted(per_tid.items()):
        row = {'tid': tid, **counts}
        has_wait = counts['epoll_pwait'] > 0 or counts['epoll_pwait2'] > 0
        has_read = counts['read'] > 0
        if has_wait and has_read:
            overlap.append(row)
        elif has_wait:
            wait_only.append(row)
        elif has_read:
            read_only.append(row)

    result = {
        'path': str(path),
        'thread_count': len(per_tid),
        'overlap_threads': overlap,
        'wait_only_threads': wait_only,
        'read_only_threads_sample': read_only[:10],
        'checker_result': (
            'late_perf_script_shows_same_thread_epoll_wait_and_read_overlap'
            if overlap else 'late_perf_script_did_not_show_same_thread_epoll_wait_and_read_overlap'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
