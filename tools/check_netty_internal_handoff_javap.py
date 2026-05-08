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
                    "error": "usage: check_netty_internal_handoff_javap.py <work-dir> <SharedGroupFactory.java> <Netty4MessageChannelHandler.java>"
                },
                indent=2,
            )
        )
        return 2

    work_dir = Path(sys.argv[1])
    shared_group_src = Path(sys.argv[2]).read_text(encoding='utf-8', errors='replace')
    handler_src = Path(sys.argv[3]).read_text(encoding='utf-8', errors='replace')
    jar = '/home/ubuntu/.gradle/caches/modules-2/files-2.1/io.netty/netty-transport/4.2.12.Final/e9d42074c3d96cf31ce57cc58f6de6f31959b7a8/netty-transport-4.2.12.Final.jar'

    javap = subprocess.run(
        ['javap', '-classpath', jar, '-c', '-p', 'io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    prod_boundary = json.loads(
        subprocess.run(
            [
                'python3',
                '/home/ubuntu/steelsearch/tools/check_netty4_handoff_gap_boundary.py',
                str(work_dir),
                sys.argv[2],
                sys.argv[3],
            ],
            capture_output=True,
            text=True,
            check=True,
        ).stdout
    )

    result = {
        'prod_boundary_result': prod_boundary['checker_result'],
        'source_transport_workers_use_nioiohandler': 'NioIoHandler.newFactory()' in shared_group_src,
        'source_netty_handler_uses_channelRead_for_pipeline_handleBytes': 'channelRead(ChannelHandlerContext ctx, Object msg)' in handler_src
        and 'pipeline.handleBytes(channel, reference);' in handler_src,
        'javap_has_doReadBytes': 'AbstractNioByteChannel.doReadBytes:(Lio/netty/buffer/ByteBuf;)I' in javap,
        'javap_has_fireChannelRead': 'ChannelPipeline.fireChannelRead:(Ljava/lang/Object;)Lio/netty/channel/ChannelPipeline;' in javap,
    }

    if (
        result['prod_boundary_result']
        == 'current_best_boundary_places_same_socket_dispatch_gap_at_netty_NioIoHandler_or_ByteBuf_handoff_before_Netty4MessageChannelHandler_channelRead'
        and result['source_transport_workers_use_nioiohandler']
        and result['source_netty_handler_uses_channelRead_for_pipeline_handleBytes']
        and result['javap_has_doReadBytes']
        and result['javap_has_fireChannelRead']
    ):
        result['checker_result'] = 'netty_javap_shows_read_path_is_doReadBytes_then_fireChannelRead_so_current_gap_is_inside_netty_internal_read_to_pipeline_handoff_before_handler_channelRead'
    else:
        result['checker_result'] = 'netty_internal_handoff_javap_boundary_incomplete'

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
