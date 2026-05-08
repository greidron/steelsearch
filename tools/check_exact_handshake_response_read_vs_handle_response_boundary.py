#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_exact_handshake_response_read_vs_handle_response_boundary.py <work-dir> <TransportHandshaker.java>'}, indent=2))
        return 2

    work_dir = Path(sys.argv[1])
    handshaker_path = Path(sys.argv[2])

    identity = json.loads(
        __import__('subprocess').run(
            [
                'python3',
                '/home/ubuntu/steelsearch/tools/check_transport_worker_29b_payload_identity.py',
                str(work_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    stdout_text = (work_dir / 'opensearch' / 'stdout.log').read_text(encoding='utf-8', errors='replace')
    handshaker_text = handshaker_path.read_text(encoding='utf-8', errors='replace')

    result = {
        'matched_handshake_response_reads': len(identity.get('matched_reads', [])),
        'handle_response_marker_count': stdout_text.count('handle_response'),
        'response_read_marker_count': stdout_text.count('response_read'),
        'listener_onResponse_marker_count': stdout_text.count('execute_handshake_listener_onResponse'),
        'listener_onFailure_marker_count': stdout_text.count('execute_handshake_listener_onFailure'),
        'source_has_handleResponse_callsite': 'handleResponse(new HandshakeResponse(' in handshaker_text or 'handleResponse(StreamInput in)' in handshaker_text,
    }

    if (
        result['matched_handshake_response_reads'] > 0
        and result['handle_response_marker_count'] == 0
        and result['response_read_marker_count'] == 0
        and result['listener_onResponse_marker_count'] == 0
        and result['listener_onFailure_marker_count'] > 0
        and result['source_has_handleResponse_callsite']
    ):
        result['checker_result'] = 'exact_low_level_handshake_response_frames_are_read_but_current_run_still_never_reaches_TransportHandshaker_handleResponse_boundary'
    else:
        result['checker_result'] = 'exact_handshake_response_read_vs_handleResponse_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
