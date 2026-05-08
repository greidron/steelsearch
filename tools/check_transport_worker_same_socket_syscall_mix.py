#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<tid>\d+)\s+\S+\s+(?P<body>.+)$")
EPOLL_RE = re.compile(r"epoll_pwait\((?P<fd>\d+)(?:<[^>]*>)?,")
PPOLL_TCP_RE = re.compile(r"ppoll\(\[\{fd=(?P<fd>\d+)<TCPv6:")
READ_TCP_RE = re.compile(r"read\((?P<fd>\d+)<TCPv6:")
READ_EVENTFD_RE = re.compile(r"read\((?P<fd>\d+)<anon_inode:\[eventfd\]>")
CLOSE_TCP_RE = re.compile(r"close\((?P<fd>\d+)<TCPv6:")
THREAD_HEADER_RE = re.compile(r'^"(?P<name>.+?)"\s+#\d+\s+\[(?P<nid_bracket>\d+)\].*?\bnid=(?P<nid>\d+)\b.*$')


def parse_transport_workers(jcmd_path: Path):
    tids = {}
    for line in jcmd_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = THREAD_HEADER_RE.match(line)
        if not m:
            continue
        name = m.group('name')
        if '[transport_worker]' not in name:
            continue
        tids[int(m.group('nid'))] = name
    return tids


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_transport_worker_same_socket_syscall_mix.py <late-strace.log> <jcmd-thread-print.txt>'}, indent=2))
        return 2

    strace_path = Path(sys.argv[1])
    jcmd_path = Path(sys.argv[2])
    transport_workers = parse_transport_workers(jcmd_path)

    counts = defaultdict(Counter)
    same_socket_tids = set()
    for raw_line in strace_path.open():
        line = raw_line.rstrip('\n')
        m = LINE_RE.match(line)
        if not m:
            continue
        tid = int(m.group('tid'))
        body = m.group('body')
        if tid not in transport_workers:
            continue
        if EPOLL_RE.search(body):
            counts[tid]['epoll_pwait'] += 1
        if PPOLL_TCP_RE.search(body):
            counts[tid]['ppoll_tcp'] += 1
            same_socket_tids.add(tid)
        if READ_TCP_RE.search(body):
            counts[tid]['read_tcp'] += 1
            same_socket_tids.add(tid)
        if READ_EVENTFD_RE.search(body):
            counts[tid]['read_eventfd'] += 1
        if CLOSE_TCP_RE.search(body):
            counts[tid]['close_tcp'] += 1
            same_socket_tids.add(tid)

    rows = []
    for tid in sorted(same_socket_tids):
        rows.append({
            'tid': tid,
            'thread_name': transport_workers.get(tid),
            'counts': dict(counts[tid]),
        })

    result = {
        'same_socket_transport_worker_tids': rows,
    }
    if rows and all(r['counts'].get('epoll_pwait', 0) > 0 for r in rows):
        result['checker_result'] = 'same_socket_transport_worker_tids_do_epoll_wait_and_tcp_ppoll_read_close_so_prior_non_selector_verdict_was_epoll_detector_miss_under_yy'
    elif rows:
        result['checker_result'] = 'same_socket_transport_worker_tids_collected_but_epoll_presence_is_mixed'
    else:
        result['checker_result'] = 'same_socket_transport_worker_tids_not_found'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
