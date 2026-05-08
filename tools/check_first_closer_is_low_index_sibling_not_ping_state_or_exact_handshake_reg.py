#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

HS_RE = re.compile(r'action-tagged selected channel index \[(\d+)\] type \[REG\] action \[internal:transport/handshake\].*localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:49761.*for \[\{rust-replica-1\}')
OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\] channel \[Netty4TcpChannel\{localAddress=/127\.0\.0\.1:(\d+), remoteAddress=127\.0\.0\.1/127\.0\.0\.1:49761\}.*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_first_closer_is_low_index_sibling_not_ping_state_or_exact_handshake_reg.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    handshake_by_port = {}
    conn_rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = HS_RE.search(line)
        if m:
            handshake_by_port[int(m.group(2))] = int(m.group(1))
            continue
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            port = int(m.group(3))
            order = int(m.group(4))
            conn_rows.setdefault(cid, []).append((order, idx, port))

    dist = Counter()
    handshake_match = 0
    ping_first = 0
    state_first = 0
    total = 0
    samples = []
    for cid, rows in sorted(conn_rows.items()):
        rows = sorted(rows)
        order, idx, port = rows[0]
        total += 1
        dist[idx] += 1
        if idx == 3:
            ping_first += 1
        if idx == 4:
            state_first += 1
        hs_idxs = sorted({handshake_by_port[p] for _, _, p in rows if p in handshake_by_port})
        if idx in hs_idxs:
            handshake_match += 1
        if len(samples) < 5:
            samples.append({'connection_id': cid, 'earliest_idx': idx, 'earliest_port': port, 'handshake_idxs': hs_idxs})

    result = 'first_closer_is_usually_low_index_sibling_not_ping_state_or_exact_handshake_reg' if total and ping_first == 0 and state_first == 0 and handshake_match == 0 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'matched_connection_count': total,
        'earliest_index_distribution': dict(sorted(dist.items())),
        'index0_first_count': dist[0],
        'exact_handshake_reg_first_count': handshake_match,
        'ping_first_count': ping_first,
        'state_first_count': state_first,
        'sample_first_five': samples,
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
