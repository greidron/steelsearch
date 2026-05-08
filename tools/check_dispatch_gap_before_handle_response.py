#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path


HANDLE_BYTES_RE = re.compile(r"steelsearch_inbound_pipeline_stage=handle_bytes remote=/127\.0\.0\.1:(\d+) length=(\d+)")


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_dispatch_gap_before_handle_response.py <work-dir> <InboundPipeline.java>'}, indent=2))
        return 2

    work_dir = Path(sys.argv[1])
    inbound_pipeline_path = Path(sys.argv[2])
    stdout_path = work_dir / 'opensearch' / 'stdout.log'

    identity = json.loads(
        subprocess.run(
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

    same_socket_ports = sorted({row['local_port'] for row in identity.get('matched_reads', [])})
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')
    handle_bytes_ports = []
    for line in stdout_text.splitlines():
        m = HANDLE_BYTES_RE.search(line)
        if m:
            handle_bytes_ports.append({'remote_port': int(m.group(1)), 'length': int(m.group(2))})

    source_has_handle_bytes_marker = 'steelsearch_inbound_pipeline_stage=handle_bytes' in inbound_pipeline_path.read_text(
        encoding='utf-8', errors='replace'
    )

    overlap = sorted({row['remote_port'] for row in handle_bytes_ports} & set(same_socket_ports))
    result = {
        'same_socket_ports_from_exact_response_reads': same_socket_ports,
        'handle_bytes_ports': handle_bytes_ports,
        'handle_bytes_overlap_with_same_socket_ports': overlap,
        'source_has_handle_bytes_marker': source_has_handle_bytes_marker,
    }

    if same_socket_ports and source_has_handle_bytes_marker and not overlap:
        result['checker_result'] = 'same_socket_exact_response_reads_occur_before_InboundPipeline_handleBytes_for_those_ports'
    else:
        result['checker_result'] = 'dispatch_gap_before_handle_response_not_fully_pinned_to_before_handleBytes'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
