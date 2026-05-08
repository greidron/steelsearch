#!/usr/bin/env python3
import json
import re
import subprocess
import sys
from pathlib import Path


NETTY_MARKER_RE = re.compile(r"steelsearch_netty4_message_channel_stage=channel_read remote=/127\.0\.0\.1:(\d+) local=")


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_production_transport_handlebytes_callsite.py <work-dir> <Netty4MessageChannelHandler.java>'}, indent=2))
        return 2

    work_dir = Path(sys.argv[1])
    source_path = Path(sys.argv[2])
    stdout_text = (work_dir / 'opensearch' / 'stdout.log').read_text(encoding='utf-8', errors='replace')
    source_text = source_path.read_text(encoding='utf-8', errors='replace')

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
    netty_ports = []
    for line in stdout_text.splitlines():
        m = NETTY_MARKER_RE.search(line)
        if m:
            netty_ports.append(int(m.group(1)))

    overlap = sorted(set(same_socket_ports) & set(netty_ports))
    result = {
        'same_socket_exact_response_ports': same_socket_ports,
        'netty_channel_read_ports': netty_ports,
        'overlap_ports': overlap,
        'source_calls_pipeline_handleBytes_in_channelRead': 'pipeline.handleBytes(channel, reference);' in source_text
        and 'steelsearch_netty4_message_channel_stage=channel_read' in source_text,
    }

    if result['source_calls_pipeline_handleBytes_in_channelRead'] and same_socket_ports and not overlap:
        result['checker_result'] = 'production_transport_handleBytes_callsite_is_Netty4MessageChannelHandler_channelRead_and_same_socket_exact_response_frames_never_reach_it'
    else:
        result['checker_result'] = 'production_transport_handleBytes_callsite_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
