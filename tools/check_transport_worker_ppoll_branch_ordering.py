#!/usr/bin/env python3
import json
import re
import sys
from collections import defaultdict
from pathlib import Path


LINE_RE = re.compile(r"^(?P<tid>\d+)\s+\S+\s+(?P<body>.+)$")
THREAD_HEADER_RE = re.compile(r'^"(?P<name>.+?)"\s+#\d+\s+\[(?P<nid_bracket>\d+)\].*?\bnid=(?P<nid>\d+)\b.*$')


def parse_transport_workers(jcmd_path: Path):
    tids = {}
    for line in jcmd_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = THREAD_HEADER_RE.match(line)
        if m and '[transport_worker]' in m.group('name'):
            tids[int(m.group('nid'))] = m.group('name')
    return tids


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_transport_worker_ppoll_branch_ordering.py <late-strace.log> <jcmd-thread-print.txt>'}, indent=2))
        return 2

    strace_path = Path(sys.argv[1])
    jcmd_path = Path(sys.argv[2])
    transport_workers = parse_transport_workers(jcmd_path)

    state = defaultdict(lambda: {
        'epoll_out_fd191': 0,
        'ppoll_pollout_fd191': 0,
        'epoll_in_fd191': 0,
        'read_fd191_29b': 0,
        'close_fd191': 0,
    })

    for raw_line in strace_path.open():
        line = raw_line.rstrip('\n')
        m = LINE_RE.match(line)
        if not m:
            continue
        tid = int(m.group('tid'))
        body = m.group('body')
        if tid not in transport_workers:
            continue

        if 'u32=191' in body and 'EPOLLOUT' in body:
            state[tid]['epoll_out_fd191'] += 1
        if 'u32=191' in body and 'EPOLLIN' in body:
            state[tid]['epoll_in_fd191'] += 1
        if 'ppoll([{fd=191<TCPv6:' in body and 'POLLOUT' in body:
            state[tid]['ppoll_pollout_fd191'] += 1
        if 'read(191<TCPv6:' in body and ') = 29 ' in body:
            state[tid]['read_fd191_29b'] += 1
        if 'close(191<TCPv6:' in body:
            state[tid]['close_fd191'] += 1

    rows = []
    for tid, counts in sorted(state.items()):
        if not any(counts.values()):
            continue
        rows.append({
            'tid': tid,
            'thread_name': transport_workers[tid],
            'counts': counts,
        })

    result = {'transport_worker_fd191_ordering': rows}
    if rows and all(
        row['counts']['epoll_out_fd191'] > 0
        and row['counts']['ppoll_pollout_fd191'] > 0
        and row['counts']['epoll_in_fd191'] > 0
        and row['counts']['read_fd191_29b'] > 0
        and row['counts']['close_fd191'] > 0
        for row in rows
    ):
        result['checker_result'] = 'transport_worker_fd191_branch_is_inline_socket_readiness_then_direct_payload_read_not_separate_helper_thread_path'
    elif rows:
        result['checker_result'] = 'transport_worker_fd191_branch_partially_observed'
    else:
        result['checker_result'] = 'transport_worker_fd191_branch_not_observed'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
