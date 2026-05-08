#!/usr/bin/env python3
import json
import re
import socket
import struct
import sys
from collections import Counter
from pathlib import Path

HEADER_RE = re.compile(r'^\s*(?P<comm>.+?)\s+(?P<tid>\d+)\s+\[[^\]]+\]\s+[0-9.]+:\s+syscalls:sys_enter_read:\s*(?P<rest>.*)$')
FD_RE = re.compile(r'fd:\s+0x(?P<fd>[0-9a-fA-F]+)')
COUNT_RE = re.compile(r'count:\s+0x(?P<count>[0-9a-fA-F]+)')
SOCK_RE = re.compile(r'^socket:\[(?P<inode>\d+)\]$')


def decode_addr_port(field: str):
    addr_hex, port_hex = field.split(':')
    ip = socket.inet_ntoa(struct.pack('<L', int(addr_hex, 16)))
    port = int(port_hex, 16)
    return ip, port


def parse_tcp_snapshot(path: Path):
    entries = {}
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    for line in lines[1:]:
        parts = line.split()
        if len(parts) < 10:
            continue
        inode = parts[9]
        local_ip, local_port = decode_addr_port(parts[1])
        remote_ip, remote_port = decode_addr_port(parts[2])
        entries[inode] = {
            'local_ip': local_ip,
            'local_port': local_port,
            'remote_ip': remote_ip,
            'remote_port': remote_port,
            'state': parts[3],
        }
    return entries


def main() -> int:
    script_path = Path(sys.argv[1])
    fd_snapshot_dir = Path(sys.argv[2])
    tcp_snapshot_dir = Path(sys.argv[3])
    capture_path = Path(sys.argv[4])

    payload_fds = Counter()
    for line in script_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = HEADER_RE.match(line)
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
    for snap in sorted(fd_snapshot_dir.glob('*.json')):
        tcp_path = tcp_snapshot_dir / snap.with_suffix('.tcp').name
        if not tcp_path.exists():
            continue
        fd_map = {int(k): v for k, v in json.loads(snap.read_text(encoding='utf-8')).items()}
        tcp_map = parse_tcp_snapshot(tcp_path)
        for fd in payload_fds:
            target = fd_map.get(fd)
            if not target:
                continue
            sm = SOCK_RE.match(target)
            if not sm:
                continue
            inode = sm.group('inode')
            entry = tcp_map.get(inode)
            if entry:
                recovered.append({
                    'snapshot': snap.name,
                    'fd': fd,
                    'inode': inode,
                    **entry,
                })

    capture = json.loads(capture_path.read_text(encoding='utf-8'))
    capture_peer_ports = sorted({int(item['peer_addr'].rsplit(':', 1)[1]) for item in capture if item.get('peer_addr')})
    capture_response_request_ids = sorted({item.get('response_frame', {}).get('request_id') for item in capture if item.get('response_frame')})
    recovered_local_ports = sorted({item['local_port'] for item in recovered})
    recovered_remote_ports = sorted({item['remote_port'] for item in recovered})

    result = {
        'script_path': str(script_path),
        'fd_snapshot_dir': str(fd_snapshot_dir),
        'tcp_snapshot_dir': str(tcp_snapshot_dir),
        'payload_fds': [{'fd': fd, 'count': c} for fd, c in payload_fds.most_common()],
        'recovered_socket_tuples': recovered[:80],
        'recovered_local_ports': recovered_local_ports,
        'recovered_remote_ports': recovered_remote_ports,
        'capture_peer_ports': capture_peer_ports,
        'capture_response_request_ids': capture_response_request_ids[:20],
        'checker_result': (
            'payload_socket_inodes_recovered_to_tcp_tuples_and_overlap_capture_peer_ports'
            if set(recovered_local_ports) & set(capture_peer_ports) else
            'payload_socket_inodes_recovered_but_did_not_overlap_capture_peer_ports'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
