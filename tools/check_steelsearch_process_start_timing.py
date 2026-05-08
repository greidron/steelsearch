#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

LAUNCH_RE = re.compile(r'Steelsearch cargo run launch epoch ms: (?P<ms>\d+)')
BIND_RE = re.compile(r'Steelsearch transport listener bound epoch_ms=(?P<ms>\d+) addr=(?P<addr>.+)')


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_steelsearch_process_start_timing.py <steelsearch-stderr.log> <report.json>', file=sys.stderr)
        return 2

    stderr_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    report = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))

    launch_match = LAUNCH_RE.search(stderr_text)
    bind_match = BIND_RE.search(stderr_text)
    captures = report.get('steelsearch_transport_capture') or []
    first_capture = min((c.get('connection_started_at_ms') for c in captures if c.get('connection_started_at_ms') is not None), default=None)

    launch_ms = int(launch_match.group('ms')) if launch_match else None
    bind_ms = int(bind_match.group('ms')) if bind_match else None
    bind_to_first_capture_ms = (first_capture - bind_ms) if bind_ms is not None and first_capture is not None else None
    launch_to_bind_ms = (bind_ms - launch_ms) if launch_ms is not None and bind_ms is not None else None
    launch_to_first_capture_ms = (first_capture - launch_ms) if launch_ms is not None and first_capture is not None else None

    result = {
        'launch_ms': launch_ms,
        'bind_ms': bind_ms,
        'bind_addr': bind_match.group('addr') if bind_match else None,
        'first_capture_ms': first_capture,
        'launch_to_bind_ms': launch_to_bind_ms,
        'bind_to_first_capture_ms': bind_to_first_capture_ms,
        'launch_to_first_capture_ms': launch_to_first_capture_ms,
        'result': 'steelsearch_process_start_timing_split_into_cargo_run_launch_to_transport_bind_and_bind_to_first_inbound_capture',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
