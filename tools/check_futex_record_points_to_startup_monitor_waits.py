#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

HEADER_RE = re.compile(r'^(?P<comm>\S+)\s+(?P<pid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_futex:')
SYMBOL_RE = re.compile(r'^\s+[0-9a-f]+\s+(?P<symbol>.+)$')


def main() -> int:
    path = Path(sys.argv[1])
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    headers = []
    symbols = Counter()
    current = None
    for line in lines:
        m = HEADER_RE.match(line)
        if m:
            current = {'comm': m.group('comm'), 'pid': int(m.group('pid'))}
            headers.append(current)
            continue
        if current is not None:
            s = SYMBOL_RE.match(line)
            if s:
                sym = s.group('symbol').strip()
                if sym:
                    symbols[sym] += 1
                continue
            if not line.strip():
                current = None

    top_symbols = [{'symbol': k, 'count': v} for k, v in symbols.most_common(10)]
    unique_pids = sorted({h['pid'] for h in headers})
    unique_comms = sorted({h['comm'] for h in headers})

    startup_markers = [
        'pthread_cond_wait+0x200 (/usr/lib/aarch64-linux-gnu/libc.so.6)',
        'PlatformMonitor::wait(unsigned long)+0x10c (/usr/lib/jvm/java-21-openjdk-arm64/lib/server/libjvm.so)',
        'Monitor::wait_without_safepoint_check(unsigned long)+0x3c (/usr/lib/jvm/java-21-openjdk-arm64/lib/server/libjvm.so)',
        'thread_native_entry(Thread*)+0x88 (/usr/lib/jvm/java-21-openjdk-arm64/lib/server/libjvm.so)',
    ]
    startup_hits = sum(symbols.get(marker, 0) for marker in startup_markers)

    result = {
        'path': str(path),
        'futex_event_headers': len(headers),
        'unique_comms': unique_comms,
        'unique_pids': unique_pids,
        'top_symbols': top_symbols,
        'startup_monitor_wait_symbol_hits': startup_hits,
        'checker_result': (
            'futex_record_points_more_directly_to_java_startup_monitor_waits_than_selector_epoll_wait'
            if startup_hits > 0 else
            'futex_record_did_not_show_expected_startup_monitor_wait_markers'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
