#!/usr/bin/env python3
import ast
import json
import re
import sys
from pathlib import Path


READ_RE = re.compile(
    r'^\d+\s+\S+\s+read\(191<TCPv6:\[\[::ffff:127\.0\.0\.1\]:(?P<local>\d+)->\[::ffff:127\.0\.0\.1\]:(?P<remote>\d+)\]>,\s+"(?P<payload>.*)",\s+2048\)\s+=\s+29\b'
)


def parse_c_escaped_bytes(payload: str) -> bytes:
    return ast.literal_eval(f'b"{payload}"')


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'error': 'usage: check_transport_worker_29b_payload_identity.py <work-dir>'}, indent=2))
        return 2

    work_dir = Path(sys.argv[1])
    strace_path = work_dir / 'opensearch' / 'late-strace.log'
    capture_path = work_dir / 'steelsearch' / 'data' / 'transport-seed-capture.json'

    capture_rows = json.loads(capture_path.read_text())
    capture_by_port = {}
    for row in capture_rows:
        peer = row.get('peer_addr')
        response = row.get('response_frame')
        if not peer or not response:
            continue
        local_port = int(peer.rsplit(':', 1)[1])
        capture_by_port[local_port] = response

    matched = []
    mismatched = []
    for line in strace_path.read_text(encoding='utf-8', errors='replace').splitlines():
        m = READ_RE.match(line)
        if not m:
            continue
        local = int(m.group('local'))
        remote = int(m.group('remote'))
        payload_bytes = parse_c_escaped_bytes(m.group('payload'))
        payload_hex = payload_bytes.hex()
        expected = capture_by_port.get(local)
        if expected is None:
            mismatched.append({
                'local_port': local,
                'remote_port': remote,
                'reason': 'missing_capture_response_frame',
                'payload_hex': payload_hex,
            })
            continue
        message_length = expected['message_length']
        expected_hex = '4553' + message_length.to_bytes(4, 'big').hex() + expected['body_prefix_hex']
        row = {
            'local_port': local,
            'remote_port': remote,
            'payload_hex': payload_hex,
            'expected_hex': expected_hex,
            'request_id': expected['request_id'],
            'status': expected['status'],
            'message_length': message_length,
            'body_len': expected['body_len'],
            'is_handshake': expected['is_handshake'],
            'is_response': expected['is_response'],
        }
        if payload_hex == expected_hex:
            matched.append(row)
        else:
            mismatched.append(row)

    result = {
        'matched_reads': matched,
        'mismatched_reads': mismatched,
    }
    if matched and not mismatched:
        result['checker_result'] = 'same_run_29b_transport_worker_reads_exactly_match_captured_low_level_tcp_handshake_response_frames'
    elif matched:
        result['checker_result'] = 'some_29b_reads_match_captured_low_level_tcp_handshake_response_frames'
    else:
        result['checker_result'] = '29b_read_identity_match_failed'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
