#!/usr/bin/env python3
import json
import re
import sys
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


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_lone_closefutureintercepted_outlier_matches_early_listener.py <artifact.json> <netty4transport.java>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    lines = stdout_log.read_text(errors='ignore').splitlines()
    first_by_connection = {}
    hint_by_port = {}
    hint_line_by_port = {}
    for i, line in enumerate(lines):
        m = FIRST_RE.search(line)
        if m:
            conn = int(m.group(1))
            index = int(m.group(2))
            port = int(m.group(3))
            order = int(m.group(4))
            cur = first_by_connection.get(conn)
            if cur is None or order < cur[0]:
                first_by_connection[conn] = (order, index, port, i)
        m = HINT_RE.search(line)
        if m:
            port = int(m.group(1))
            hint_by_port[port] = m.group(2)
            hint_line_by_port[port] = i

    outliers = []
    for conn, (_order, index, port, first_line_idx) in sorted(first_by_connection.items()):
        hint = hint_by_port.get(port)
        if hint == 'closeFutureIntercepted':
            outliers.append((conn, index, port, first_line_idx, hint_line_by_port[port]))

    source = Path(sys.argv[2]).read_text()
    has_listener = 'private void addEarlyCloseFutureHintListener(Channel channel)' in source
    has_closefuture_set = 'channel.attr(Netty4TcpChannel.CLOSE_HINT_KEY).set("closeFutureIntercepted")' in source
    has_early_channelinactive = 'tcpChannel.recordCloseHint("earlyChannelInactive", null);' in source

    details = []
    for conn, index, port, first_line_idx, hint_line_idx in outliers:
        next_channelinactive_delta = None
        next_early_channelinactive_delta = None
        for i in range(hint_line_idx + 1, len(lines)):
            line = lines[i]
            if str(port) not in line:
                continue
            if 'netty4 message channel handler channelInactive on' in line:
                next_channelinactive_delta = i - hint_line_idx
                break
        for i in range(hint_line_idx + 1, len(lines)):
            line = lines[i]
            if str(port) not in line:
                continue
            if 'earlyChannelInactive' in line:
                next_early_channelinactive_delta = i - hint_line_idx
                break
        details.append({
            'connection_id': conn,
            'index': index,
            'port': port,
            'hint_line_index': hint_line_idx,
            'message_channelinactive_after_lines': next_channelinactive_delta,
            'early_channelinactive_after_lines': next_early_channelinactive_delta,
        })

    result = (
        'lone_closefutureintercepted_outlier_best_matches_netty4transport_early_close_future_listener_winning_before_later_channelinactive_hints'
        if len(outliers) == 1 and has_listener and has_closefuture_set and details[0]['message_channelinactive_after_lines'] is not None
        else 'inconclusive'
    )

    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'source_has_add_early_close_future_hint_listener': has_listener,
        'source_sets_closeFutureIntercepted_when_hint_null': has_closefuture_set,
        'source_has_early_channelinactive_handler': has_early_channelinactive,
        'closefutureintercepted_first_close_outlier_count': len(outliers),
        'outliers': details,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
