#!/usr/bin/env python3
import json
import re
import sys
from collections import Counter
from pathlib import Path

READ_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
FD_RE = re.compile(r'fd:\s+0x(?P<fd>[0-9a-fA-F]+)')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
SS_RE = re.compile(r'^(?P<state>\S+)\s+\d+\s+\d+\s+(?P<local>\S+)\s+(?P<peer>\S+)\s+users:\(\("(?P<comm>.+?)",pid=(?P<pid>\d+),fd=(?P<fd>\d+)\)\)')


def split_port(addr: str):
    host, port = addr.rsplit(':', 1)
    return host, int(port)


def main() -> int:
    script_path = Path(sys.argv[1])
    ss_snapshot_dir = Path(sys.argv[2])
    capture_path = Path(sys.argv[3])

    payload_fds = Counter()
    for line in script_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = READ_RE.match(line)
        if not m:
            continue
        rest = m.group('rest')
        fdm = FD_RE.search(rest)
        cm = COUNT_RE.search(rest)
        if not fdm or not cm:
            continue
        fd = int(fdm.group('fd'), 16)
        count = int(cm.group('count'), 16)
        if count >= 1024:
            payload_fds[fd] += 1

    recovered = []
    for snap in sorted(ss_snapshot_dir.glob('*.ss')):
        for line in snap.read_text(encoding='utf-8', errors='replace').splitlines():
            m = SS_RE.match(line.strip())
            if not m:
                continue
            fd = int(m.group('fd'))
            if fd not in payload_fds:
                continue
            local_host, local_port = split_port(m.group('local'))
            peer_host, peer_port = split_port(m.group('peer'))
            recovered.append({
                'snapshot': snap.name,
                'fd': fd,
                'comm': m.group('comm'),
                'pid': int(m.group('pid')),
                'state': m.group('state'),
                'local_host': local_host,
                'local_port': local_port,
                'peer_host': peer_host,
                'peer_port': peer_port,
            })

    capture = json.loads(capture_path.read_text(encoding='utf-8'))
    capture_peer_ports = sorted({int(item['peer_addr'].rsplit(':', 1)[1]) for item in capture if item.get('peer_addr')})
    recovered_local_ports = sorted({item['local_port'] for item in recovered})
    recovered_peer_ports = sorted({item['peer_port'] for item in recovered})

    result = {
        'payload_fds': [{'fd': fd, 'count': c} for fd, c in payload_fds.most_common()],
        'recovered_tuples': recovered[:120],
        'recovered_local_ports': recovered_local_ports,
        'recovered_peer_ports': recovered_peer_ports,
        'capture_peer_ports': capture_peer_ports,
        'checker_result': (
            'ss_snapshots_mapped_payload_fds_to_live_port_tuples_and_overlap_capture_peer_ports'
            if set(recovered_local_ports) & set(capture_peer_ports) else
            'ss_snapshots_mapped_payload_fds_to_live_port_tuples_without_capture_peer_port_overlap'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
