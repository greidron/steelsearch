#!/usr/bin/env python3
import json
import socket
import struct
import sys
from pathlib import Path


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
    fd_snapshot_dir = Path(sys.argv[1])
    tcp_snapshot_dir = Path(sys.argv[2])
    capture_path = Path(sys.argv[3])
    fd = int(sys.argv[4])

    recovered = []
    for snap in sorted(fd_snapshot_dir.glob('*.json')):
        fdmap = {int(k): v for k, v in json.loads(snap.read_text()).items()}
        target = fdmap.get(fd)
        if not target or not target.startswith('socket:['):
            continue
        inode = target[len('socket:['):-1]
        tcp_entries = parse_tcp_snapshot(tcp_snapshot_dir / snap.with_suffix('.tcp').name)
        if inode in tcp_entries:
            recovered.append({'snapshot': snap.name, 'fd': fd, 'inode': inode, **tcp_entries[inode]})

    capture = json.loads(capture_path.read_text(encoding='utf-8'))
    capture_peer_ports = sorted({int(item['peer_addr'].rsplit(':', 1)[1]) for item in capture if item.get('peer_addr')})
    recovered_local_ports = sorted({item['local_port'] for item in recovered})
    recovered_remote_ports = sorted({item['remote_port'] for item in recovered})

    result = {
        'fd': fd,
        'recovered_socket_tuples': recovered,
        'recovered_local_ports': recovered_local_ports,
        'recovered_remote_ports': recovered_remote_ports,
        'capture_peer_ports': capture_peer_ports,
        'checker_result': (
            'payload_fd191_tcp_tuples_overlap_capture_peer_ports'
            if set(recovered_local_ports) & set(capture_peer_ports) else
            'payload_fd191_tcp_tuples_do_not_overlap_capture_peer_ports'
        ),
    }
    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
