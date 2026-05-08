#!/usr/bin/env python3
import argparse
import json
import re
from pathlib import Path


def find(pattern: str, text: str, label: str) -> str:
    m = re.search(pattern, text, re.MULTILINE)
    if not m:
        raise SystemExit(f'missing {label}')
    return m.group(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--opensearch-root', required=True)
    parser.add_argument('--report-path', required=True)
    args = parser.parse_args()

    root = Path(args.opensearch_root)
    tcp_header = (root / 'server/src/main/java/org/opensearch/transport/TcpHeader.java').read_text(encoding='utf-8')
    tcp_transport = (root / 'server/src/main/java/org/opensearch/transport/TcpTransport.java').read_text(encoding='utf-8')
    handshaker = (root / 'server/src/main/java/org/opensearch/transport/TransportHandshaker.java').read_text(encoding='utf-8')
    transport_service = (root / 'server/src/main/java/org/opensearch/transport/TransportService.java').read_text(encoding='utf-8')

    report = {
        'marker_prefix': 'ES',
        'marker_bytes_size': int(find(r'MARKER_BYTES_SIZE = (\d+);', tcp_header, 'marker size')),
        'message_length_size': int(find(r'MESSAGE_LENGTH_SIZE = (\d+);', tcp_header, 'message length size')),
        'request_id_size': int(find(r'REQUEST_ID_SIZE = (\d+);', tcp_header, 'request id size')),
        'status_size': int(find(r'STATUS_SIZE = (\d+);', tcp_header, 'status size')),
        'version_id_size': int(find(r'VERSION_ID_SIZE = (\d+);', tcp_header, 'version id size')),
        'variable_header_size_size': int(find(r'VARIABLE_HEADER_SIZE = (\d+);', tcp_header, 'variable header size')),
        'bytes_required_for_message_size': int(find(r'BYTES_REQUIRED_FOR_MESSAGE_SIZE = ([A-Z_+0-9 ]+);', tcp_header, 'bytes required').replace('MARKER_BYTES_SIZE + MESSAGE_LENGTH_SIZE', '6') if 'MARKER_BYTES_SIZE + MESSAGE_LENGTH_SIZE' in find(r'BYTES_REQUIRED_FOR_MESSAGE_SIZE = ([A-Z_+0-9 ]+);', tcp_header, 'bytes required') else find(r'BYTES_REQUIRED_FOR_MESSAGE_SIZE = (\d+);', tcp_header, 'bytes required literal')),
        'tcp_handshake_action': find(r'HANDSHAKE_ACTION_NAME = "([^"]+)";', handshaker, 'tcp handshake action'),
        'transport_identity_handshake_action': find(r'HANDSHAKE_ACTION_NAME = "([^"]+)";', transport_service, 'transport handshake action'),
        'client_initiates_handshake': True,
        'server_validates_prefix': 'headerBuffer.get(0) != \'E\' || headerBuffer.get(1) != \'S\'' in tcp_transport,
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
