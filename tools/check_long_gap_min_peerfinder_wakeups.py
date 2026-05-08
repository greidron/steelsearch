#!/usr/bin/env python3
import json
import math
import re
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def parse_find_peers_interval_ms(text: str):
    m = re.search(r'DISCOVERY_FIND_PEERS_INTERVAL_SETTING.*?TimeValue\.timeValueMillis\((\d+)\)', text, re.S)
    return int(m.group(1)) if m else None


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_long_gap_min_peerfinder_wakeups.py <PeerFinder.java> <retry_gap_paths.json>')

    source = Path(sys.argv[1]).read_text()
    retry = load(sys.argv[2])

    find_peers_interval_ms = parse_find_peers_interval_ms(source)
    delayed_entries = retry.get('delayed_entries') or []
    delayed_gap_ms = delayed_entries[0].get('gap_ms') if len(delayed_entries) == 1 else None
    min_wakeups = math.ceil(delayed_gap_ms / find_peers_interval_ms) if delayed_gap_ms is not None and find_peers_interval_ms else None

    result = (
        'long_gap_exception_requires_many_peerfinder_wakeup_rounds'
        if min_wakeups is not None and min_wakeups >= 10
        else 'long_gap_min_peerfinder_wakeups_not_fully_established'
    )

    print(json.dumps({
        'find_peers_interval_ms': find_peers_interval_ms,
        'delayed_gap_ms': delayed_gap_ms,
        'min_wakeups': min_wakeups,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
