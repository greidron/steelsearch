#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

READ_HEADER_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
STACK_RE = re.compile(r'^\s+[0-9a-f]+\s+(?P<symbol>.+)$')


def main() -> int:
    path = Path(sys.argv[1])
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    resolved_after_read0 = Counter()
    payload_events = 0
    unknown_after_read0 = 0
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
            sym = sm.group('symbol').strip()
            if 'Java_sun_nio_ch_UnixFileDispatcherImpl_read0' in sym:
                saw_read0 = True
            elif saw_read0:
                if '[unknown]' in sym:
                    unknown_after_read0 += 1
                else:
                    resolved_after_read0[sym] += 1
            j += 1
        i = j
    result = {
        'path': str(path),
        'payload_event_count': payload_events,
        'resolved_after_read0': [{'symbol': s, 'count': c} for s, c in resolved_after_read0.most_common(20)],
        'unknown_after_read0_count': unknown_after_read0,
    }
    if resolved_after_read0:
        result['checker_result'] = 'perf_dwarf_candidate_recovered_non_unknown_higher_caller_frames_after_read0'
    else:
        result['checker_result'] = 'perf_dwarf_candidate_did_not_recover_non_unknown_higher_caller_frames_after_read0'
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
