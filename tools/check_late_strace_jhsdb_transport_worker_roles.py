#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

THREAD_RE = re.compile(r'^"(?P<name>.+?)".* nid=(?:0x[0-9a-f]+|(?P<nid_dec>\d+))', re.I)
STRACE_TID_RE = re.compile(r'^\s*(\d+)\s+')
TCP_TID_RE = re.compile(r'^\s*(\d+).*TCPv6')


def parse_same_socket_tids(strace_text):
    tids = set()
    for line in strace_text.splitlines():
        m = TCP_TID_RE.match(line)
        if m:
            tids.add(int(m.group(1)))
    return sorted(tids)


def parse_threads(jhsdb_text):
    mapping = {}
    for line in jhsdb_text.splitlines():
        m = THREAD_RE.match(line.strip())
        if not m:
            continue
        name = m.group('name')
        text = line.strip()
        mhex = re.search(r'nid=0x([0-9a-f]+)', text, re.I)
        if mhex:
            tid = int(mhex.group(1), 16)
        else:
            mdec = re.search(r'nid=(\d+)', text)
            if not mdec:
                continue
            tid = int(mdec.group(1))
        mapping[tid] = name
    return mapping


def main():
    if len(sys.argv) != 3:
        print('usage: check_late_strace_jhsdb_transport_worker_roles.py <late-strace.log> <jhsdb-jstack.txt>')
        return 2
    strace_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
    jhsdb_text = Path(sys.argv[2]).read_text(encoding='utf-8', errors='ignore')
    tids = parse_same_socket_tids(strace_text)
    mapping = parse_threads(jhsdb_text)
    mapped = {str(t): mapping[t] for t in tids if t in mapping}
    transport_worker = {k: v for k, v in mapped.items() if '[transport_worker]' in v}
    result = 'undetermined'
    if transport_worker:
        result = 'late_strace_same_socket_tcp_tids_are_visible_in_jhsdb_and_map_to_transport_worker_threads'
    print(json.dumps({
        'checker_result': result,
        'same_socket_tcp_tids': tids,
        'mapped_tids': mapped,
        'transport_worker_tids': transport_worker,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
