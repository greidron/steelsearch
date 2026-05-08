#!/usr/bin/env python3
import argparse
import json
import socket
import struct
import time
from pathlib import Path


def write_vint(i: int) -> bytes:
    if i < 0:
        i &= 0xFFFFFFFF
    out = bytearray()
    while (i & ~0x7F) != 0:
        out.append((i & 0x7F) | 0x80)
        i >>= 7
    out.append(i & 0x7F)
    return bytes(out)


def write_string(s: str) -> bytes:
    return write_vint(len(s)) + s.encode('utf-8')


def write_string_array(items: list[str]) -> bytes:
    out = bytearray(write_vint(len(items)))
    for item in items:
        out.extend(write_string(item))
    return bytes(out)


def write_bytes_reference(b: bytes) -> bytes:
    return write_vint(len(b)) + b


def build_handshake_request(version_id: int, request_id: int, action: str) -> bytes:
    status = 0b1000  # request + handshake
    variable_header = b''
    variable_header += write_vint(0)  # request headers map size
    variable_header += write_vint(0)  # response headers map size
    variable_header += write_string_array([])
    variable_header += write_string(action)

    payload = b''
    payload += write_string('')  # EMPTY_TASK_ID nodeId
    version_payload = write_vint(version_id)
    payload += write_bytes_reference(version_payload)

    content = variable_header + payload
    message_length = len(content) + 8 + 1 + 4 + 4

    frame = bytearray()
    frame.extend(b'ES')
    frame.extend(struct.pack('>i', message_length))
    frame.extend(struct.pack('>q', request_id))
    frame.append(status)
    frame.extend(struct.pack('>i', version_id))
    frame.extend(struct.pack('>i', len(variable_header)))
    frame.extend(content)
    return bytes(frame)


def recv_exact(sock: socket.socket, wanted: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < wanted:
        chunk = sock.recv(wanted - len(chunks))
        if not chunk:
            break
        chunks.extend(chunk)
    return bytes(chunks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', required=True)
    parser.add_argument('--port', required=True, type=int)
    parser.add_argument('--version-id', type=int, default=3070099)
    parser.add_argument('--request-id', type=int, default=1)
    parser.add_argument('--action', default='internal:tcp/handshake')
    parser.add_argument('--frame-hex')
    parser.add_argument('--timeout-seconds', type=float, default=2.0)
    parser.add_argument('--report-path', required=True)
    args = parser.parse_args()

    request_bytes = bytes.fromhex(args.frame_hex) if args.frame_hex else build_handshake_request(args.version_id, args.request_id, args.action)
    report = {
        'request_frame_source': 'frame_hex' if args.frame_hex else 'python_builder',
        'host': args.host,
        'port': args.port,
        'version_id': args.version_id,
        'request_id': args.request_id,
        'action': args.action,
        'request_bytes_len': len(request_bytes),
        'request_prefix_hex': request_bytes[:16].hex(),
        'tcp_connected': False,
        'request_sent': False,
        'response_received': False,
        'response_bytes_len': 0,
        'response_prefix_hex': '',
        'response_hex': '',
        'response_starts_with_es': False,
        'error': None,
        'elapsed_seconds': None,
    }

    started = time.time()
    try:
        with socket.create_connection((args.host, args.port), timeout=args.timeout_seconds) as sock:
            report['tcp_connected'] = True
            sock.settimeout(args.timeout_seconds)
            sock.sendall(request_bytes)
            report['request_sent'] = True
            try:
                response_header = recv_exact(sock, 6)
            except socket.timeout:
                response_header = b''
            response = response_header
            if len(response_header) == 6 and response_header[:2] == b'ES':
                response_length = struct.unpack('>i', response_header[2:6])[0]
                try:
                    response_tail = recv_exact(sock, response_length)
                except socket.timeout:
                    response_tail = b''
                response = response_header + response_tail
            if response:
                report['response_received'] = True
                report['response_bytes_len'] = len(response)
                report['response_prefix_hex'] = response[:16].hex()
                report['response_hex'] = response.hex()
                report['response_starts_with_es'] = response.startswith(b'ES')
    except Exception as exc:
        report['error'] = f'{type(exc).__name__}: {exc}'
    finally:
        report['elapsed_seconds'] = round(time.time() - started, 3)

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0 if report['request_sent'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
