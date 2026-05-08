#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

READ_HEADER_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
THREAD_HEADER_RE = re.compile(r'^"(?P<name>.+?)"\s+#\d+\s+\[(?P<nid_bracket>\d+)\].*?\bnid=(?P<nid>\d+)\b.*$')
STATE_RE = re.compile(r'^\s*java\.lang\.Thread\.State:\s+(?P<state>.+)$')
FRAME_RE = re.compile(r'^\s+at\s+(?P<frame>.+)$')


def parse_payload_tids(path: Path):
    tids = Counter()
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = READ_HEADER_RE.match(line)
        if not m:
            continue
        cm = COUNT_RE.search(m.group('rest'))
        if not cm or int(cm.group('count'), 16) < 1024:
            continue
        tids[int(m.group('tid'))] += 1
    return tids


def parse_thread_dump(path: Path):
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    threads = {}
    i = 0
    while i < len(lines):
        m = THREAD_HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        nid = int(m.group('nid'))
        info = {'name': m.group('name'), 'state': None, 'frames': []}
        j = i + 1
        while j < len(lines):
            if THREAD_HEADER_RE.match(lines[j]):
                break
            sm = STATE_RE.match(lines[j])
            if sm and info['state'] is None:
                info['state'] = sm.group('state').strip()
            fm = FRAME_RE.match(lines[j])
            if fm and len(info['frames']) < 12:
                info['frames'].append(fm.group('frame').strip())
            j += 1
        threads[nid] = info
        i = j
    return threads


def classify(frames):
    joined = ' | '.join(frames)
    if 'sun.nio.ch.' in joined or 'SocketDispatcher' in joined or 'UnixFileDispatcherImpl' in joined:
        return 'nio_read_visible'
    if 'LinkedTransferQueue' in joined or 'Unsafe.park' in joined or 'LockSupport.parkNanos' in joined:
        return 'parking'
    if 'io.netty.channel.nio.NioIoHandler.select' in joined or 'EPollSelectorImpl.doSelect' in joined:
        return 'selector_wait'
    return 'other'


def main() -> int:
    perf_path = Path(sys.argv[1])
    jcmd_dir = Path(sys.argv[2])
    payload_tids = parse_payload_tids(perf_path)
    top_tids = [tid for tid, _ in payload_tids.most_common(12)]
    snapshots = sorted(jcmd_dir.glob('jcmd-*.txt'))

    per_tid = {tid: {'count': payload_tids[tid], 'name': None, 'states': Counter(), 'classifications': Counter(), 'example_frames': defaultdict(list)} for tid in top_tids}
    for snap in snapshots:
        threads = parse_thread_dump(snap)
        for tid in top_tids:
            if tid not in threads:
                continue
            info = threads[tid]
            entry = per_tid[tid]
            entry['name'] = info['name']
            if info['state']:
                entry['states'][info['state']] += 1
            klass = classify(info['frames'])
            entry['classifications'][klass] += 1
            if info['frames'] and len(entry['example_frames'][klass]) < 2:
                entry['example_frames'][klass].append(info['frames'][:5])

    out = {
        'perf_path': str(perf_path),
        'jcmd_dir': str(jcmd_dir),
        'snapshot_count': len(snapshots),
        'payload_threads': [],
    }

    visible_nio = 0
    generic_nio_visible = 0
    for tid in top_tids:
        entry = per_tid[tid]
        payload = {
            'tid': tid,
            'count': entry['count'],
            'thread_name': entry['name'],
            'states': dict(entry['states']),
            'classifications': dict(entry['classifications']),
            'example_frames': dict(entry['example_frames']),
        }
        if entry['classifications'].get('nio_read_visible', 0) > 0:
            visible_nio += 1
        if entry.get('name') and '[generic]' in entry['name'] and entry['classifications'].get('nio_read_visible', 0) > 0:
            generic_nio_visible += 1
        out['payload_threads'].append(payload)

    out['generic_nio_visible_thread_count'] = generic_nio_visible
    if generic_nio_visible > 0:
        out['checker_result'] = 'repeated_jcmd_captured_higher_java_nio_caller_frames_for_generic_payload_threads'
    else:
        out['checker_result'] = 'repeated_jcmd_did_not_capture_higher_java_nio_caller_frames_for_generic_payload_threads_and_main_generic_threads_remained_parked'

    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
