#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_tcp_handshake_response_shape_matches_probe.py <transport-handshake.json> <transport-seed-capture.json>', file=sys.stderr)
        return 2

    probe = json.loads(Path(sys.argv[1]).read_text())
    capture = json.loads(Path(sys.argv[2]).read_text())

    probe_response_hex = probe['response_hex']
    probe_body_hex = probe_response_hex[12:]

    matched = None
    for entry in capture:
        first = entry.get('first_frame') or {}
        response = entry.get('response_frame') or {}
        if first.get('action_hint') == 'internal:tcp/handshake' and response.get('is_response') and response.get('is_handshake'):
            matched = entry
            break

    if matched is None:
        print('probe_body_hex', probe_body_hex)
        print('matched_capture_entry=false')
        print('checker_result=inconclusive')
        return 0

    response = matched['response_frame']
    capture_body_prefix = response.get('body_prefix_hex')
    print('probe_body_hex', probe_body_hex)
    print('capture_body_prefix_hex', capture_body_prefix)
    print('probe_response_bytes_len', probe.get('response_bytes_len'))
    print('capture_message_length', response.get('message_length'))
    print('capture_connection_end', matched.get('connection_end'))

    if capture_body_prefix == probe_body_hex:
        print('checker_result=tcp_handshake_response_shape_matches_probe_so_current_issue_is_not_raw_response_serialization_mismatch')
    else:
        print('checker_result=inconclusive')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
