#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            json.dumps(
                {
                    "error": "usage: check_netty4_handoff_gap_boundary.py <work-dir> <SharedGroupFactory.java> <Netty4MessageChannelHandler.java>"
                },
                indent=2,
            )
        )
        return 2

    work_dir = Path(sys.argv[1])
    shared_group_src = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    handler_src = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')

    prod_callsite = json.loads(
        subprocess.run(
            [
                'python3',
                '/home/ubuntu/steelsearch/tools/check_production_transport_handlebytes_callsite.py',
                str(work_dir),
                sys.argv[3],
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    payload_boundary = json.loads(
        subprocess.run(
            [
                'python3',
                '/home/ubuntu/steelsearch/tools/check_transport_worker_payload_read_vs_java_markers.py',
                str(work_dir),
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    result = {
        'prod_callsite_result': prod_callsite['checker_result'],
        'payload_boundary_result': payload_boundary['checker_result'],
        'source_transport_workers_use_netty_nioiohandler': 'MultiThreadIoEventLoopGroup(' in shared_group_src
        and 'TcpTransport.TRANSPORT_WORKER_THREAD_NAME_PREFIX' in shared_group_src
        and 'NioIoHandler.newFactory()' in shared_group_src,
        'source_channelRead_calls_pipeline_handleBytes': 'channelRead(ChannelHandlerContext ctx, Object msg)' in handler_src
        and 'pipeline.handleBytes(channel, reference);' in handler_src,
    }

    if (
        result['source_transport_workers_use_netty_nioiohandler']
        and result['source_channelRead_calls_pipeline_handleBytes']
        and prod_callsite['checker_result']
        == 'production_transport_handleBytes_callsite_is_Netty4MessageChannelHandler_channelRead_and_same_socket_exact_response_frames_never_reach_it'
        and payload_boundary['checker_result']
        == 'same_run_transport_worker_payload_reads_exist_but_java_response_markers_stay_zero_so_boundary_is_above_socket_read_and_below_netty_response_dispatch'
    ):
        result['checker_result'] = 'current_best_boundary_places_same_socket_dispatch_gap_at_netty_NioIoHandler_or_ByteBuf_handoff_before_Netty4MessageChannelHandler_channelRead'
    else:
        result['checker_result'] = 'netty4_handoff_gap_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
