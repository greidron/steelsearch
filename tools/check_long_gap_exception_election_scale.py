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
        raise SystemExit('usage: check_long_gap_exception_election_scale.py <ElectionSchedulerFactory.java> <retry_gap_paths.json>')

    source = Path(sys.argv[1]).read_text()
    retry = load(sys.argv[2])

    initial_timeout_ms = parse_ms(r'ELECTION_INITIAL_TIMEOUT_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', source)
    backoff_ms = parse_ms(r'ELECTION_BACK_OFF_TIME_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', source)
    max_timeout_ms = parse_seconds_ms(r'ELECTION_MAX_TIMEOUT_SETTING.*?TimeValue\.timeValueSeconds\((\d+)\)', source)
    duration_ms = parse_ms(r'ELECTION_DURATION_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', source)

    delayed_entries = retry.get('delayed_entries') or []
    delayed_gap_ms = delayed_entries[0].get('gap_ms') if len(delayed_entries) == 1 else None
    aligns_with_election_scale = (
        delayed_gap_ms is not None
        and max_timeout_ms is not None
        and duration_ms is not None
        and delayed_gap_ms > max_timeout_ms
        and delayed_gap_ms < max_timeout_ms * 2
    )

    result = (
        'long_gap_exception_is_more_consistent_with_election_scheduler_scale_than_1s_probe_scale'
        if aligns_with_election_scale and initial_timeout_ms == 100 and backoff_ms == 100
        else 'long_gap_exception_election_scale_not_fully_established'
    )

    print(json.dumps({
        'election_initial_timeout_ms': initial_timeout_ms,
        'election_backoff_ms': backoff_ms,
        'election_max_timeout_ms': max_timeout_ms,
        'election_duration_ms': duration_ms,
        'delayed_gap_ms': delayed_gap_ms,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
