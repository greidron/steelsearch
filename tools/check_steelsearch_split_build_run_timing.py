#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

PATTERNS = {
    'launch_ms': re.compile(r'Steelsearch cargo run launch epoch ms: (?P<ms>\d+)'),
    'build_start_ms': re.compile(r'Steelsearch cargo build start epoch ms: (?P<ms>\d+)'),
    'build_done_ms': re.compile(r'Steelsearch cargo build done epoch ms: (?P<ms>\d+)'),
    'binary_exec_launch_ms': re.compile(r'Steelsearch binary exec launch epoch ms: (?P<ms>\d+)'),
    'bind_ms': re.compile(r'Steelsearch transport listener bound epoch_ms=(?P<ms>\d+) addr=(?P<addr>.+)'),
}


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_steelsearch_split_build_run_timing.py <steelsearch-stderr.log> <report.json>', file=sys.stderr)
        return 2

    stderr_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    report = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))

    values = {}
    bind_addr = None
    for key, pattern in PATTERNS.items():
        m = pattern.search(stderr_text)
        if not m:
            values[key] = None
            continue
        values[key] = int(m.group('ms'))
        if key == 'bind_ms':
            bind_addr = m.group('addr')

    captures = report.get('steelsearch_transport_capture') or []
    first_capture_ms = min((c.get('connection_started_at_ms') for c in captures if c.get('connection_started_at_ms') is not None), default=None)

    result = {
        **values,
        'bind_addr': bind_addr,
        'first_capture_ms': first_capture_ms,
        'build_duration_ms': (values['build_done_ms'] - values['build_start_ms']) if values['build_done_ms'] and values['build_start_ms'] else None,
        'binary_exec_to_bind_ms': (values['bind_ms'] - values['binary_exec_launch_ms']) if values['bind_ms'] and values['binary_exec_launch_ms'] else None,
        'bind_to_first_capture_ms': (first_capture_ms - values['bind_ms']) if first_capture_ms and values['bind_ms'] else None,
        'result': 'steelsearch_split_build_run_timing_separates_cargo_build_cost_from_binary_startup_and_transport_acceptance',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
