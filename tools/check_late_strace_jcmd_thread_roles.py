#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


TUPLE_RE = re.compile(
    r"^(?P<tid>\d+)\s+\S+\s+.*TCPv6:\[\[::ffff:127\.0\.0\.1\]:(?P<local>\d+)->\[::ffff:127\.0\.0\.1\]:(?P<remote>\d+)\].*$"
)
THREAD_HEADER_RE = re.compile(r'^"(?P<name>.+?)"\s+#\d+\s+\[(?P<nid_bracket>\d+)\].*?\bnid=(?P<nid>\d+)\b.*$')


def classify_role(name: str) -> str:
    if '[transport_worker]' in name:
        return 'opensearch_transport_worker'
    if '[generic]' in name:
        return 'opensearch_generic'
    if '[scheduler]' in name:
        return 'opensearch_scheduler'
    if 'keepAlive/' in name:
        return 'opensearch_keepalive'
    return 'other'


def parse_tuple_tids(path: Path):
    rows = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = TUPLE_RE.match(line)
        if not m:
            continue
        tid = int(m.group('tid'))
        row = rows.setdefault(tid, {'local_ports': set(), 'remote_ports': set(), 'count': 0})
        row['local_ports'].add(int(m.group('local')))
        row['remote_ports'].add(int(m.group('remote')))
        row['count'] += 1
    return rows


def parse_threads(path: Path):
    threads = {}
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = THREAD_HEADER_RE.match(line)
        if not m:
            continue
        nid = int(m.group('nid'))
        name = m.group('name')
        threads[nid] = {'name': name, 'role': classify_role(name)}
    return threads


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_late_strace_jcmd_thread_roles.py <late-strace.log> <jcmd-thread-print.txt>'}, indent=2))
        return 2

    tuple_rows = parse_tuple_tids(Path(sys.argv[1]))
    threads = parse_threads(Path(sys.argv[2]))

    mapped = []
    missing = []
    for tid in sorted(tuple_rows):
        base = {
            'tid': tid,
            'tuple_event_count': tuple_rows[tid]['count'],
            'local_ports': sorted(tuple_rows[tid]['local_ports']),
            'remote_ports': sorted(tuple_rows[tid]['remote_ports']),
        }
        thread = threads.get(tid)
        if thread is None:
            missing.append(base)
            continue
        mapped.append({
            **base,
            'thread_name': thread['name'],
            'role': thread['role'],
        })

    roles = {row['role'] for row in mapped}
    result = {
        'mapped_tuple_threads': mapped,
        'missing_tuple_threads': missing,
    }
    if mapped and roles == {'opensearch_generic'}:
        result['checker_result'] = 'late_strace_same_socket_non_selector_tids_map_cleanly_to_opensearch_generic_pool'
    elif mapped:
        result['checker_result'] = 'late_strace_same_socket_non_selector_tids_map_to_mixed_java_roles'
    else:
        result['checker_result'] = 'late_strace_same_socket_non_selector_tids_failed_to_map_to_jcmd_threads'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
