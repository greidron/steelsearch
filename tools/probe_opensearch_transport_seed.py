#!/usr/bin/env python3
import argparse
import json
import socket
import time
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--timeout-seconds', type=float, default=3.0)
    parser.add_argument('--report-path', required=True)
    args = parser.parse_args()

    started = time.time()
    report = {
        'host': args.host,
        'port': args.port,
        'timeout_seconds': args.timeout_seconds,
        'tcp_connected': False,
        'peer_speaks_first': False,
        'peer_closed_immediately': False,
        'first_bytes_hex': '',
        'first_bytes_len': 0,
        'error': None,
        'elapsed_seconds': None,
    }

    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout_seconds) as sock:
            report['tcp_connected'] = True
            sock.settimeout(args.timeout_seconds)
            try:
                data = sock.recv(64)
            except socket.timeout:
                data = b''
            if data:
                report['peer_speaks_first'] = True
                report['first_bytes_hex'] = data.hex()
                report['first_bytes_len'] = len(data)
            else:
                try:
                    sock.settimeout(0.25)
                    data2 = sock.recv(1)
                except socket.timeout:
                    data2 = None
                if data2 == b'':
                    report['peer_closed_immediately'] = True
                elif data2:
                    report['peer_speaks_first'] = True
                    combined = data + data2
                    report['first_bytes_hex'] = combined.hex()
                    report['first_bytes_len'] = len(combined)
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        report['elapsed_seconds'] = round(time.time() - started, 3)

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['tcp_connected'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
