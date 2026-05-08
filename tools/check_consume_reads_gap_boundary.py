#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            json.dumps(
                {
                    "error": "usage: check_consume_reads_gap_boundary.py <work-dir> <BytesChannelContext.java> <InboundPipeline.java> <MockNioTransport.java>"
                },
                indent=2,
            )
        )
        return 2

    work_dir = Path(sys.argv[1])
    bytes_ctx = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    pipeline_src = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')
    mock_src = Path(sys.argv[4]).read_text(encoding='utf-8', errors='replace')

    dispatch_gap = json.loads(
        subprocess.run(
            [
                'python3',
                '/home/ubuntu/steelsearch/tools/check_dispatch_gap_before_handle_response.py',
                str(work_dir),
                sys.argv[3],
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    result = {
        'dispatch_gap_result': dispatch_gap['checker_result'],
        'same_socket_ports': dispatch_gap['same_socket_ports_from_exact_response_reads'],
        'handle_bytes_ports': dispatch_gap['handle_bytes_ports'],
        'bytes_channel_context_reads_then_handleReadBytes': 'int bytesRead = readFromChannel(channelBuffer);' in bytes_ctx
        and 'handleReadBytes();' in bytes_ctx,
        'socket_channel_context_handleReadBytes_calls_consumeReads': 'channelHandler.consumeReads(channelBuffer);' in Path(
            '/home/ubuntu/OpenSearch/libs/nio/src/main/java/org/opensearch/nio/SocketChannelContext.java'
        ).read_text(encoding='utf-8', errors='replace'),
        'mock_consumeReads_calls_pipeline_handleBytes': 'pipeline.handleBytes(channel, reference);' in mock_src,
        'pipeline_has_handle_bytes_marker': 'steelsearch_inbound_pipeline_stage=handle_bytes' in pipeline_src,
    }

    if (
        result['dispatch_gap_result'] == 'same_socket_exact_response_reads_occur_before_InboundPipeline_handleBytes_for_those_ports'
        and result['bytes_channel_context_reads_then_handleReadBytes']
        and result['socket_channel_context_handleReadBytes_calls_consumeReads']
        and result['mock_consumeReads_calls_pipeline_handleBytes']
        and result['pipeline_has_handle_bytes_marker']
    ):
        result['checker_result'] = 'current_best_boundary_places_same_socket_dispatch_gap_at_or_before_production_NioChannelHandler_consumeReads_before_InboundPipeline_handleBytes'
    else:
        result['checker_result'] = 'consumeReads_gap_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
