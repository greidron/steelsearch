#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

SEL_RE = re.compile(r'action-tagged selected channel index \[(\d+)\] type \[(\w+)\] action \[([^\]]+)\].*for \[\{rust-replica-1\}')
OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_low_index_first_closer_points_to_idle_bulk_recovery_siblings.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    selected = Counter()
    earliest = Counter()
    conn_rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = SEL_RE.search(line)
        if m:
            selected[int(m.group(1))] += 1
            continue
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            order = int(m.group(3))
            conn_rows.setdefault(cid, []).append((order, idx))
    for cid, rows in conn_rows.items():
        earliest[sorted(rows)[0][1]] += 1

    low_idle_first = sum(earliest[i] for i in (1, 2, 5, 6))
    low_idle_selected = sum(selected[i] for i in (1, 2, 5, 6))
    result = 'low_index_first_close_points_away_from_bulk_recovery_action_pressure_and_toward_idle_unused_sibling_pressure' if low_idle_first > 0 and low_idle_selected == 0 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'selected_index_counts': dict(sorted(selected.items())),
        'earliest_index_distribution': dict(sorted(earliest.items())),
        'idle_low_index_first_count_1_2_5_6': low_idle_first,
        'idle_low_index_selected_count_1_2_5_6': low_idle_selected,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
