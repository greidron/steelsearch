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


def family(index: int) -> str:
    if index <= 2:
        return 'BULK'
    if index == 3:
        return 'PING'
    if index == 4:
        return 'STATE'
    if index <= 6:
        return 'RECOVERY'
    return 'REG'


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_unknown_free_hint_distribution_by_family.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    lines = stdout_log.read_text(errors='ignore').splitlines()

    hints_by_port = {}
    for line in lines:
        m = HINT_RE.search(line)
        if m:
            hints_by_port[int(m.group(1))] = m.group(2)

    first_by_connection = {}
    for line in lines:
        m = FIRST_RE.search(line)
        if not m:
            continue
        conn = int(m.group(1))
        index = int(m.group(2))
        port = int(m.group(3))
        order = int(m.group(4))
        cur = first_by_connection.get(conn)
        if cur is None or order < cur[0]:
            first_by_connection[conn] = (order, index, port)

    first_family_hint = Counter()
    for _conn, (_order, index, port) in first_by_connection.items():
        first_family_hint[(family(index), hints_by_port.get(port, 'missing'))] += 1

    selected_by_port = defaultdict(set)
    for line in lines:
        m = SELECT_RE.search(line)
        if not m:
            continue
        index = int(m.group(1))
        action = m.group(3)
        port = int(m.group(5))
        selected_by_port[port].add((family(index), action))

    selected_family_hint = Counter()
    selected_action_hint = Counter()
    for port, items in selected_by_port.items():
        hint = hints_by_port.get(port, 'missing')
        for fam in {fam for fam, _action in items}:
            selected_family_hint[(fam, hint)] += 1
        for action in {action for _fam, action in items}:
            selected_action_hint[(action, hint)] += 1

    unknown_total = sum(1 for hint in hints_by_port.values() if hint == 'unknown')
    action_explicit_only = all(hint == 'explicitLocalClose' for (_a, hint) in selected_action_hint)
    first_close_explicit = sum(count for (fam, hint), count in first_family_hint.items() if hint == 'explicitLocalClose')
    first_close_non_explicit = sum(count for (fam, hint), count in first_family_hint.items() if hint != 'explicitLocalClose')
    result = (
        'named_node_hint_distribution_is_dominated_by_explicit_local_close_across_action_bearing_and_first_close_families'
        if action_explicit_only and first_close_explicit > first_close_non_explicit
        else 'inconclusive'
    )

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'unknown_total': unknown_total,
        'first_close_explicit_count': first_close_explicit,
        'first_close_non_explicit_count': first_close_non_explicit,
        'first_close_family_hint_distribution': {
            f'{fam}|{hint}': count for (fam, hint), count in sorted(first_family_hint.items())
        },
        'selected_family_hint_distribution': {
            f'{fam}|{hint}': count for (fam, hint), count in sorted(selected_family_hint.items())
        },
        'selected_action_hint_distribution': {
            f'{action}|{hint}': count for (action, hint), count in sorted(selected_action_hint.items())
        },
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
