#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

READ_HEADER_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
STACK_RE = re.compile(r'^\s+(?P<addr>[0-9a-f]+)\s+(?P<symbol>.+)$')
MAP_RE = re.compile(r'^(?P<start>[0-9a-fA-F]+)\s+(?P<size>[0-9a-fA-F]+)\s+(?P<name>.+)$')


def load_map(path: Path):
    ranges = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = MAP_RE.match(line.strip())
        if not m:
            continue
        start = int(m.group('start'), 16)
        size = int(m.group('size'), 16)
        ranges.append((start, start + size, m.group('name').strip()))
    ranges.sort()
    return ranges


def symbolize(addr: int, ranges):
    for start, end, name in ranges:
        if start <= addr < end:
            return name
    return None


def main() -> int:
    perf_script = Path(sys.argv[1])
    perf_map = Path(sys.argv[2])
    ranges = load_map(perf_map)
    lines = perf_script.read_text(encoding='utf-8', errors='replace').splitlines()

    resolved = Counter()
    unresolved = 0
    payload_events = 0
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
        payload_events += 1
        saw_read0 = False
        j = i + 1
        while j < len(lines):
            sm = STACK_RE.match(lines[j])
            if not sm:
                break
            addr = int(sm.group('addr'), 16)
            symbol = sm.group('symbol').strip()
            if 'Java_sun_nio_ch_UnixFileDispatcherImpl_read0' in symbol:
                saw_read0 = True
            elif saw_read0 and '(/tmp/perf-' in symbol:
                name = symbolize(addr, ranges)
                if name:
                    resolved[name] += 1
                else:
                    unresolved += 1
            j += 1
        i = j

    out = {
        'perf_script': str(perf_script),
        'perf_map': str(perf_map),
        'map_entry_count': len(ranges),
        'payload_event_count': payload_events,
        'resolved_symbols': [{'symbol': s, 'count': c} for s, c in resolved.most_common(20)],
        'unresolved_after_read0_count': unresolved,
    }
    if resolved:
        out['checker_result'] = 'perf_map_symbolized_higher_jit_frames_above_unixfiledispatcher_read0'
    else:
        out['checker_result'] = 'perf_map_did_not_symbolize_higher_jit_frames_above_unixfiledispatcher_read0'
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
