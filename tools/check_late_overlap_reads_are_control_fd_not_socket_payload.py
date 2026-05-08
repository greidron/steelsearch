#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict, Counter
from pathlib import Path

HEADER_RE = re.compile(
    r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+(?P<event>syscalls:sys_enter_[^:]+):\s*(?P<rest>.*)$'
)
FD_RE = re.compile(r'fd:\s+0x(?P<fd>[0-9a-fA-F]+)')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
EPFD_RE = re.compile(r'epfd:\s+0x(?P<epfd>[0-9a-fA-F]+)')


def main() -> int:
    path = Path(sys.argv[1])
    per_tid = defaultdict(lambda: {
        'comm': None,
        'read_fds': Counter(),
        'read_sizes': Counter(),
        'epoll_fds': Counter(),
        'read': 0,
        'epoll_pwait': 0,
        'epoll_pwait2': 0,
    })

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
            bucket['read'] += 1
            fdm = FD_RE.search(rest)
            cm = COUNT_RE.search(rest)
            if fdm:
                bucket['read_fds'][int(fdm.group('fd'), 16)] += 1
            if cm:
                bucket['read_sizes'][int(cm.group('count'), 16)] += 1
        elif event in ('epoll_pwait', 'epoll_pwait2'):
            bucket[event] += 1
            em = EPFD_RE.search(rest)
            if em:
                bucket['epoll_fds'][int(em.group('epfd'), 16)] += 1

    overlap = []
    read_only = []
    for tid, bucket in sorted(per_tid.items()):
        has_wait = bucket['epoll_pwait'] > 0 or bucket['epoll_pwait2'] > 0
        has_read = bucket['read'] > 0
        row = {
            'tid': tid,
            'comm': bucket['comm'],
            'read': bucket['read'],
            'epoll_pwait': bucket['epoll_pwait'],
            'epoll_pwait2': bucket['epoll_pwait2'],
            'top_read_fds': [{'fd': fd, 'count': c} for fd, c in bucket['read_fds'].most_common(5)],
            'top_read_sizes': [{'size': sz, 'count': c} for sz, c in bucket['read_sizes'].most_common(5)],
            'top_epoll_fds': [{'fd': fd, 'count': c} for fd, c in bucket['epoll_fds'].most_common(5)],
        }
        if has_wait and has_read:
            overlap.append(row)
        elif has_read:
            read_only.append(row)

    overlap_small_read_only = all(
        all(item['size'] <= 16 for item in row['top_read_sizes']) for row in overlap if row['top_read_sizes']
    )
    read_only_has_payload = any(
        any(item['size'] >= 1024 for item in row['top_read_sizes']) for row in read_only
    )

    result = {
        'path': str(path),
        'overlap_threads': overlap,
        'read_only_threads_sample': read_only[:10],
        'overlap_small_read_only': overlap_small_read_only,
        'read_only_has_payload_sized_reads': read_only_has_payload,
        'checker_result': (
            'late_overlap_threads_read_control_sized_fds_while_payload_sized_socket_reads_happen_on_other_threads'
            if overlap_small_read_only and read_only_has_payload else
            'late_overlap_fd_pattern_did_not_cleanly_separate_control_reads_from_payload_reads'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
