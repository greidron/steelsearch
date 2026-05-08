#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

HS_RE = re.compile(r'action-tagged selected channel index \[(\d+)\] type \[REG\] action \[internal:transport/handshake\].*localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:49761.*for \[\{rust-replica-1\}')
OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:49761\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_first_closer_matches_handshake_used_reg_sibling.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    handshake_by_port = {}
    conn_rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = HS_RE.search(line)
        if m:
            idx = int(m.group(1))
            port = int(m.group(2))
            handshake_by_port[port] = idx
            continue
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            port = int(m.group(3))
            order = int(m.group(4))
            conn_rows.setdefault(cid, []).append((order, idx, port))

    matched = []
    for cid, rows in sorted(conn_rows.items()):
        rows = sorted(rows)
        earliest_order, earliest_idx, earliest_port = rows[0]
        handshake_idxs = sorted({handshake_by_port[port] for _, _, port in rows if port in handshake_by_port})
        if not handshake_idxs:
            continue
        # one named multichannel handshake port per connection is expected
        matched.append({
            'connection_id': cid,
            'earliest_idx': earliest_idx,
            'earliest_port': earliest_port,
            'handshake_idxs': handshake_idxs,
            'matches_handshake_idx': earliest_idx in handshake_idxs,
        })

    total = len(matched)
    handshake_first = sum(x['matches_handshake_idx'] for x in matched)
    reg_first = sum(7 <= x['earliest_idx'] <= 12 for x in matched)
    ping_first = sum(x['earliest_idx'] == 3 for x in matched)
    state_first = sum(x['earliest_idx'] == 4 for x in matched)
    result = 'handshake_used_reg_idle_sibling_is_the_dominant_first_closer_in_the_connection_level_teardown_cascade' if total and handshake_first > max(ping_first, state_first) else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'matched_connection_count': total,
        'handshake_first_match_count': handshake_first,
        'reg_first_count': reg_first,
        'ping_first_count': ping_first,
        'state_first_count': state_first,
        'sample_first_five': matched[:5],
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
