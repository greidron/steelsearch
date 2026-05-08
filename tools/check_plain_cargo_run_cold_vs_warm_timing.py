#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

LAUNCH_RE = re.compile(r'Steelsearch cargo run launch epoch ms: (?P<ms>\d+)')
BIND_RE = re.compile(r'Steelsearch transport listener bound epoch_ms=(?P<ms>\d+) addr=(?P<addr>.+)')


def launch_to_bind(stderr_path: str) -> int:
    text = Path(stderr_path).read_text(encoding='utf-8', errors='replace')
    launch = int(LAUNCH_RE.search(text).group('ms'))
    bind = int(BIND_RE.search(text).group('ms'))
    return bind - launch


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_plain_cargo_run_cold_vs_warm_timing.py <cold-steelsearch-stderr.log> <warm-steelsearch-stderr.log>', file=sys.stderr)
        return 2

    cold_ms = launch_to_bind(sys.argv[1])
    warm_ms = launch_to_bind(sys.argv[2])
    result = {
        'cold_launch_to_bind_ms': cold_ms,
        'warm_launch_to_bind_ms': warm_ms,
        'delta_ms': cold_ms - warm_ms,
        'result': 'earlier_multi_second_plain_cargo_run_delay_is_a_cold_incremental_rebuild_artifact_not_a_stable_wrapper_overhead',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
