#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

READ_HEADER_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
STACK_RE = re.compile(r'^\s+[0-9a-f]+\s+(?P<symbol>.+)$')
THREAD_HEADER_RE = re.compile(
    r'^"(?P<name>.+?)"\s+#\d+\s+\[(?P<nid_bracket>\d+)\].*?\bnid=(?P<nid>\d+)\b.*$'
)
STATE_RE = re.compile(r'^\s*java\.lang\.Thread\.State:\s+(?P<state>.+)$')
FRAME_RE = re.compile(r'^\s+at\s+(?P<frame>.+)$')


def parse_payload_tids(path: Path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    tids = Counter()
    symbols = {}
    i = 0
    while i < len(lines):
        m = READ_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        cm = COUNT_RE.search(m.group('rest'))
        if not cm or int(cm.group('count'), 16) < 1024:
            i += 1
            continue
        tid = int(m.group('tid'))
        tids[tid] += 1
        frames = []
        j = i + 1
        while j < len(lines):
            sm = STACK_RE.match(lines[j])
            if not sm:
                break
            frames.append(sm.group('symbol').strip())
            j += 1
        if tid not in symbols:
            symbols[tid] = frames[:8]
        i = j
    return tids, symbols


def parse_jcmd_threads(path: Path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    threads = {}
    i = 0
    while i < len(lines):
        m = THREAD_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        nid = int(m.group('nid'))
        info = {
            'name': m.group('name'),
            'nid': nid,
            'state': None,
            'top_java_frames': [],
        }
        j = i + 1
        while j < len(lines):
            if THREAD_HEADER_RE.match(lines[j]):
                break
            sm = STATE_RE.match(lines[j])
            if sm and info['state'] is None:
                info['state'] = sm.group('state').strip()
            fm = FRAME_RE.match(lines[j])
            if fm and len(info['top_java_frames']) < 8:
                info['top_java_frames'].append(fm.group('frame').strip())
            j += 1
        threads[nid] = info
        i = j
    return threads


def classify_role(name: str) -> str:
    if '[transport_worker]' in name:
        return 'opensearch_transport_worker'
    if '[http_worker]' in name:
        return 'opensearch_http_worker'
    if '[generic]' in name:
        return 'opensearch_generic'
    return 'other'


def main() -> int:
    perf_path = Path(sys.argv[1])
    jcmd_path = Path(sys.argv[2])

    tids, perf_symbols = parse_payload_tids(perf_path)
    threads = parse_jcmd_threads(jcmd_path)

    mapped = []
    role_counts = Counter()
    missing = []
    for tid, count in tids.most_common(12):
        thread = threads.get(tid)
        if thread is None:
            missing.append({'tid': tid, 'count': count})
            continue
        role = classify_role(thread['name'])
        role_counts[role] += count
        mapped.append({
            'tid': tid,
            'count': count,
            'thread_name': thread['name'],
            'role': role,
            'state': thread['state'],
            'jcmd_top_java_frames': thread['top_java_frames'][:5],
            'perf_top_symbols': perf_symbols.get(tid, [])[:5],
        })

    result = {
        'perf_path': str(perf_path),
        'jcmd_path': str(jcmd_path),
        'payload_event_count': sum(tids.values()),
        'mapped_payload_threads': mapped,
        'missing_payload_tids': missing,
        'role_counts': dict(role_counts),
    }

    if role_counts.get('opensearch_generic', 0) > role_counts.get('opensearch_transport_worker', 0):
        result['checker_result'] = 'main_payload_read_only_threads_map_to_opensearch_generic_pool_while_transport_worker_reads_are_only_occasional'
    elif role_counts.get('opensearch_transport_worker', 0) > 0 and not missing:
        result['checker_result'] = 'payload_read_only_threads_map_to_opensearch_transport_worker_event_loop_threads'
    elif role_counts:
        result['checker_result'] = 'payload_read_only_threads_mapped_but_not_cleanly_to_transport_worker_only'
    else:
        result['checker_result'] = 'payload_read_only_threads_failed_to_map_to_jcmd_threads'

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
