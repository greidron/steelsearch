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
    top_symbols = Counter()
    payload_events = 0
    tids = Counter()
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
        tids[int(m.group('tid'))] += 1
        j = i + 1
        while j < len(lines):
            s = STACK_RE.match(lines[j])
            if not s:
                break
            sym = s.group('symbol').strip()
            if sym:
                top_symbols[sym] += 1
            j += 1
        i = j

    result = {
        'path': str(path),
        'payload_event_count': payload_events,
        'payload_tids': [{'tid': tid, 'count': c} for tid, c in tids.most_common(10)],
        'top_stack_symbols': [{'symbol': s, 'count': c} for s, c in top_symbols.most_common(12)],
        'checker_result': (
            'payload_read_only_path_reaches_jdk_nio_unixfiledispatcher_read0_before_any_higher_netty_marker'
            if any('Java_sun_nio_ch_UnixFileDispatcherImpl_read0' in s for s in top_symbols)
            else 'payload_read_stack_did_not_show_expected_jdk_nio_read0_marker'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
