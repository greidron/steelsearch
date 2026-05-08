#!/usr/bin/env python3
import argparse
import json
import struct
from pathlib import Path


def read_vint(data: bytes, offset: int):
    shift = 0
    value = 0
    pos = offset
    while True:
        b = data[pos]
        pos += 1
        value |= (b & 0x7F) << shift
        if (b & 0x80) == 0:
            return value, pos
        shift += 7


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--response-hex', required=True)
    parser.add_argument('--report-path', required=True)
    args = parser.parse_args()

    raw = bytes.fromhex(args.response_hex)
    pos = 0
    marker = raw[pos:pos+2].decode('ascii'); pos += 2
    message_length = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    request_id = struct.unpack('>q', raw[pos:pos+8])[0]; pos += 8
    status = raw[pos]; pos += 1
    version_id = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    variable_header_size = struct.unpack('>i', raw[pos:pos+4])[0]; pos += 4
    variable_header = raw[pos:pos+variable_header_size]; pos += variable_header_size
    response_version_id, pos = read_vint(raw, pos)

    report = {
        'marker_prefix': marker,
        'message_length': message_length,
        'request_id': request_id,
        'status': status,
        'is_response': bool(status & 0x01),
        'is_handshake': bool(status & 0x08),
        'header_version_id': version_id,
        'variable_header_size': variable_header_size,
        'variable_header_hex': variable_header.hex(),
        'tcp_handshake_response_version_id': response_version_id,
        'peer_identity_present': False,
        'remaining_bytes_after_version': raw[pos:].hex(),
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
