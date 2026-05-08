#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

FIRST_RE = re.compile(
    r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel '
    r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*for '\
    r'\[\{rust-replica-1\}.*closeOrder \[(\d+)\]'
)
HINT_RE = re.compile(
    r'netty4 tcp channel close completed for '\
    r'\[\[id: [^,]+, L:/127\.0\.0\.1:(\d+) ! R:[^\]]+\]\] with hint \[([^\]]+)\]'
)
SELECT_RE = re.compile(
    r'action-tagged selected channel index \[(\d+)\] type \[([^\]]+)\] action '\
    r'\[([^\]]+)\] requestId \[(\d+)\] channel '\
    r'\[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), .*for '\
    r'\[\{rust-replica-1\}.*'
)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_early_closefuture_residue_is_benign_for_model.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    lines = stdout_log.read_text(errors='ignore').splitlines()

    hints = {}
    for line in lines:
        m = HINT_RE.search(line)
        if m:
            hints[int(m.group(1))] = m.group(2)

    first_by_conn = {}
    for line in lines:
        m = FIRST_RE.search(line)
        if not m:
            continue
        conn = int(m.group(1))
        idx = int(m.group(2))
        port = int(m.group(3))
        order = int(m.group(4))
        cur = first_by_conn.get(conn)
        if cur is None or order < cur[0]:
            first_by_conn[conn] = (order, idx, port)

    first_hint_counts = Counter()
    for _conn, (_order, _idx, port) in first_by_conn.items():
        first_hint_counts[hints.get(port, 'missing')] += 1

    selected_action_hint = Counter()
    seen_action_ports = defaultdict(set)
    for line in lines:
        m = SELECT_RE.search(line)
        if not m:
            continue
        action = m.group(3)
        port = int(m.group(5))
        seen_action_ports[action].add(port)
    for action, ports in seen_action_ports.items():
        for port in ports:
            selected_action_hint[(action, hints.get(port, 'missing'))] += 1

    action_non_explicit = sum(
        count for (action, hint), count in selected_action_hint.items() if hint != 'explicitLocalClose'
    )
    first_total = sum(first_hint_counts.values())
    residue = first_hint_counts.get('closeFutureIntercepted', 0)
    residue_ratio = residue / first_total if first_total else 0.0
    result = (
        'single_closefutureintercepted_residue_is_benign_for_the_current_stale_sibling_close_model'
        if residue == 1 and residue_ratio < 0.02 and action_non_explicit == 0
        else 'inconclusive'
    )

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'first_close_hint_distribution': dict(sorted(first_hint_counts.items())),
        'first_close_total': first_total,
        'closefutureintercepted_residue_count': residue,
        'closefutureintercepted_residue_ratio': residue_ratio,
        'action_non_explicit_count': action_non_explicit,
        'selected_action_hint_distribution': {
            f'{action}|{hint}': count for (action, hint), count in sorted(selected_action_hint.items())
        },
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
