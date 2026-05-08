#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 4:
        print('usage: check_netty_cfr_relief_candidate.py <work-dir> <decompiled-AbstractNioByteChannel.java> <decompiled-AbstractChannelHandlerContext.java>')
        return 2

    work_dir = Path(sys.argv[1])
    nio_src = Path(sys.argv[2]).read_text()
    ctx_src = Path(sys.argv[3]).read_text()
    stdout = (work_dir / 'opensearch' / 'stdout.log').read_text()

    nio_facts = {
        'doReadBytes_then_fireChannelRead': 'allocHandle.lastBytesRead(AbstractNioByteChannel.this.doReadBytes(byteBuf));' in nio_src and 'pipeline.fireChannelRead(byteBuf);' in nio_src,
        'readComplete_after_loop': 'allocHandle.readComplete();' in nio_src and 'pipeline.fireChannelReadComplete();' in nio_src,
        'closeOnRead_path': 'this.closeOnRead(pipeline);' in nio_src,
    }
    ctx_facts = {
        'findContextInbound_32': 'AbstractChannelHandlerContext next = this.findContextInbound(32);' in ctx_src,
        'same_thread_direct_handler_call': '((ChannelInboundHandler)handler).channelRead(next, m);' in ctx_src,
        'async_executor_fallback': 'next.executor().execute(() -> this.fireChannelRead(msg));' in ctx_src,
    }
    marker_counts = {
        'response_read': stdout.count('steelsearch_handshake_stage=response_read'),
        'handle_response': stdout.count('steelsearch_handshake_stage=handle_response'),
        'netty_channel_read': stdout.count('steelsearch_netty4_message_channel_stage=channel_read'),
    }

    result = 'undetermined'
    if all(nio_facts.values()) and all(ctx_facts.values()) and marker_counts['response_read'] == 0 and marker_counts['handle_response'] == 0 and marker_counts['netty_channel_read'] == 1:
        result = 'cfr_decompile_is_a_materially_different_netty_visibility_capability_but_it_still_reconfirms_the_same_repo_external_internal_handoff_boundary'

    print(json.dumps({
        'checker_result': result,
        'nio_facts': nio_facts,
        'ctx_facts': ctx_facts,
        'marker_counts': marker_counts,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
