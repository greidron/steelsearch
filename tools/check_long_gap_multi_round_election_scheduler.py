#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def parse_ms(pattern: str, text: str):
    m = re.search(pattern, text, re.S)
    return int(m.group(1)) if m else None


def parse_seconds_ms(pattern: str, text: str):
    m = re.search(pattern, text, re.S)
    return int(m.group(1)) * 1000 if m else None


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_long_gap_multi_round_election_scheduler.py <ElectionSchedulerFactory.java> <retry_gap_paths.json>')

    source = Path(sys.argv[1]).read_text()
    retry = load(sys.argv[2])

    max_timeout_ms = parse_seconds_ms(r'ELECTION_MAX_TIMEOUT_SETTING.*?TimeValue\.timeValueSeconds\((\d+)\)', source)
    duration_ms = parse_ms(r'ELECTION_DURATION_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', source)
    delayed_entries = retry.get('delayed_entries') or []
    delayed_gap_ms = delayed_entries[0].get('gap_ms') if len(delayed_entries) == 1 else None

    single_round_upper_bound_ms = (max_timeout_ms + duration_ms) if max_timeout_ms is not None and duration_ms is not None else None
    multi_round_candidate = (
        delayed_gap_ms is not None and single_round_upper_bound_ms is not None
        and delayed_gap_ms > single_round_upper_bound_ms
        and delayed_gap_ms < single_round_upper_bound_ms * 2
    )

    result = (
        'long_gap_exception_fits_multi_round_election_scheduler_scale_better_than_single_round_or_1s_probe'
        if multi_round_candidate
        else 'long_gap_multi_round_election_scheduler_scale_not_fully_established'
    )

    print(json.dumps({
        'election_max_timeout_ms': max_timeout_ms,
        'election_duration_ms': duration_ms,
        'single_round_upper_bound_ms': single_round_upper_bound_ms,
        'delayed_gap_ms': delayed_gap_ms,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
