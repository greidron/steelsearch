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
EPFD_RE = re.compile(r'epfd:\s+0x(?P<epfd>[0-9a-fA-F]+)')


def main() -> int:
    script_path = Path(sys.argv[1])
    snapshot_path = Path(sys.argv[2])
    snapshot = {int(k): v for k, v in json.loads(snapshot_path.read_text(encoding='utf-8')).items()}

    per_tid = defaultdict(lambda: {'comm': None, 'read_fds': Counter(), 'epoll_fds': Counter(), 'read': 0, 'epoll_pwait': 0, 'epoll_pwait2': 0})
    for line in script_path.read_text(encoding='utf-8', errors='replace').splitlines():
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
            if fdm:
                bucket['read_fds'][int(fdm.group('fd'), 16)] += 1
        elif event in ('epoll_pwait', 'epoll_pwait2'):
            bucket[event] += 1
            em = EPFD_RE.search(rest)
            if em:
                bucket['epoll_fds'][int(em.group('epfd'), 16)] += 1

    overlap = []
    read_only = []
    for tid, bucket in sorted(per_tid.items()):
        row = {'tid': tid, 'comm': bucket['comm']}
        row['read_fds'] = [{'fd': fd, 'count': c, 'target': snapshot.get(fd)} for fd, c in bucket['read_fds'].most_common(5)]
        row['epoll_fds'] = [{'fd': fd, 'count': c, 'target': snapshot.get(fd)} for fd, c in bucket['epoll_fds'].most_common(5)]
        has_wait = bucket['epoll_pwait'] > 0 or bucket['epoll_pwait2'] > 0
        has_read = bucket['read'] > 0
        if has_wait and has_read:
            overlap.append(row)
        elif has_read:
            read_only.append(row)

    overlap_epoll_targets = [item['target'] for row in overlap for item in row['epoll_fds']]
    overlap_read_targets = [item['target'] for row in overlap for item in row['read_fds']]
    read_only_targets = [item['target'] for row in read_only[:10] for item in row['read_fds']]

    result = {
        'script_path': str(script_path),
        'snapshot_path': str(snapshot_path),
        'overlap_threads': overlap,
        'read_only_threads_sample': read_only[:10],
        'checker_result': (
            'epoll_fds_map_to_eventpoll_and_payload_fds_map_to_sockets_in_late_window'
            if all(t and 'anon_inode:[eventpoll]' in t for t in overlap_epoll_targets)
            and any(t and t.startswith('socket:[') for t in overlap_read_targets)
            and any(t and t.startswith('socket:[') for t in read_only_targets)
            else 'fd_snapshot_did_not_cleanly_map_epoll_and_payload_roles'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
