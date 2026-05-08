#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

OBS_RE = re.compile(r'node connection \[(\d+)\] observed close on channelIndex \[(\d+)\].*for \[\{rust-replica-1\}.*closeOrder \[(\d+)\]')


def main():
    if len(sys.argv) != 2:
        print('usage: check_index0_is_excluded_because_it_is_the_bringup_handshake_channel.py <artifact.json>', file=sys.stderr)
        return 2
    artifact = json.loads(Path(sys.argv[1]).read_text())
    stdout_log = Path(artifact['work_dir']) / 'opensearch' / 'stdout.log'
    src = Path('/home/ubuntu/OpenSearch/server/src/main/java/org/opensearch/transport/TcpTransport.java').read_text(errors='ignore')
    source_uses_channel0_for_bringup_handshake = 'final TcpChannel handshakeChannel = channels.get(0);' in src and 'executeHandshake(node, handshakeChannel, connectionProfile' in src

    rows = {}
    for line in stdout_log.read_text(errors='ignore').splitlines():
        m = OBS_RE.search(line)
        if m:
            cid = int(m.group(1))
            idx = int(m.group(2))
            order = int(m.group(3))
            rows.setdefault(cid, []).append((order, idx))
    first = Counter(sorted(v)[0][1] for v in rows.values())
    result = 'index0_is_excluded_from_idle_first_close_because_it_is_the_pre_nodechannels_bringup_handshake_channel' if source_uses_channel0_for_bringup_handshake and first[0] == 0 else 'inconclusive'
    print(json.dumps({
        'work_dir': artifact['work_dir'],
        'source_uses_channel0_for_bringup_handshake': source_uses_channel0_for_bringup_handshake,
        'first_index_distribution': dict(sorted(first.items())),
        'index0_first_count': first[0],
        'result': result,
    }, indent=2, ensure_ascii=False))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
