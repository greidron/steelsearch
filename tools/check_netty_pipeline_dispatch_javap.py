#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def run_json(cmd):
    return json.loads(subprocess.check_output(cmd, text=True))


def run_text(cmd):
    return subprocess.check_output(cmd, text=True)


def main():
    if len(sys.argv) != 3:
        print('usage: check_netty_pipeline_dispatch_javap.py <work-dir> <netty-transport-jar>')
        return 2

    work_dir = Path(sys.argv[1])
    jar = sys.argv[2]

    achc = run_text([
        'javap', '-classpath', jar, '-c', '-p',
        'io.netty.channel.AbstractChannelHandlerContext',
    ])

    identity = run_json([
        'python3', '/home/ubuntu/steelsearch/tools/check_transport_worker_29b_payload_identity.py',
        str(work_dir),
    ])
    markers = run_json([
        'python3', '/home/ubuntu/steelsearch/tools/check_transport_worker_payload_read_vs_java_markers.py',
        str(work_dir),
    ])
    callsite = run_json([
        'python3', '/home/ubuntu/steelsearch/tools/check_production_transport_handlebytes_callsite.py',
        str(work_dir),
        '/home/ubuntu/OpenSearch/modules/transport-netty4/src/main/java/org/opensearch/transport/netty4/Netty4MessageChannelHandler.java',
    ])

    javap_facts = {
        'fireChannelRead_method': 'public io.netty.channel.ChannelHandlerContext fireChannelRead(java.lang.Object);' in achc,
        'findContextInbound_32': 'bipush        32' in achc and 'findContextInbound:(I)Lio/netty/channel/AbstractChannelHandlerContext;' in achc,
        'executor_in_event_loop_gate': 'EventExecutor.inEventLoop:()Z' in achc,
        'invoke_handler_gate': 'invokeHandler:()Z' in achc,
        'direct_channelRead_invoke': 'ChannelInboundHandler.channelRead:(Lio/netty/channel/ChannelHandlerContext;Ljava/lang/Object;)V' in achc,
        'async_executor_fallback': 'EventExecutor.execute:(Ljava/lang/Runnable;)V' in achc and 'lambda$fireChannelRead$2' in achc,
    }

    result = 'undetermined'
    if (
        all(javap_facts.values())
        and identity['checker_result'] == 'same_run_29b_transport_worker_reads_exactly_match_captured_low_level_tcp_handshake_response_frames'
        and markers['transport_worker_tcp_payload_read_29b_count'] > 0
        and markers['java_marker_counts']['response_read'] == 0
        and markers['java_marker_counts']['handle_response'] == 0
        and callsite['source_calls_pipeline_handleBytes_in_channelRead']
        and not callsite['overlap_ports']
    ):
        result = 'netty_pipeline_dispatch_javap_does_not_narrow_beyond_same_thread_fireChannelRead_or_async_executor_split_so_current_session_best_boundary_is_repo_external_netty_internal_handoff_practical_stop'

    out = {
        'checker_result': result,
        'javap_facts': javap_facts,
        'same_run_facts': {
            'matched_handshake_reads': len(identity['matched_reads']),
            'same_socket_exact_response_ports': callsite['same_socket_exact_response_ports'],
            'channel_read_ports': callsite['netty_channel_read_ports'],
            'overlap_ports': callsite['overlap_ports'],
            'java_marker_counts': markers['java_marker_counts'],
        },
    }
    print(json.dumps(out, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
