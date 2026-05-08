#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def parse_json_or_die(path_str: str):
    path = Path(path_str)
    return path, json.loads(path.read_text(encoding='utf-8'))


def main() -> int:
    mapping_path, mapping = parse_json_or_die(sys.argv[1])
    tcp_path = Path(sys.argv[2])
    transport_service_path = Path(sys.argv[3])
    handshaker_path = Path(sys.argv[4])

    tcp_text = tcp_path.read_text(encoding='utf-8', errors='replace')
    ts_text = transport_service_path.read_text(encoding='utf-8', errors='replace')
    handshaker_text = handshaker_path.read_text(encoding='utf-8', errors='replace')

    generic_count = mapping.get('role_counts', {}).get('opensearch_generic', 0)
    transport_count = mapping.get('role_counts', {}).get('opensearch_transport_worker', 0)
    main_threads = [
        t for t in mapping.get('mapped_payload_threads', [])
        if t.get('role') == 'opensearch_generic'
    ]

    result = {
        'mapping_path': str(mapping_path),
        'generic_payload_event_count': generic_count,
        'transport_worker_payload_event_count': transport_count,
        'main_generic_threads': [
            {
                'tid': t['tid'],
                'count': t['count'],
                'thread_name': t['thread_name'],
                'perf_symbol': t['perf_top_symbols'][1] if len(t.get('perf_top_symbols', [])) > 1 else None,
            }
            for t in main_threads[:5]
        ],
        'tcptransport_wraps_open_connection_listener_on_generic': 'new ThreadedActionListener<>(logger, threadPool, ThreadPool.Names.GENERIC, listener, false)' in tcp_text,
        'tcptransport_schedules_connect_timeout_on_generic': 'threadPool.schedule(channelsConnectedListener::onTimeout, connectTimeout, ThreadPool.Names.GENERIC);' in tcp_text,
        'transportservice_handshake_response_handler_on_generic': '}, HandshakeResponse::new, ThreadPool.Names.GENERIC)' in ts_text,
        'transport_handshaker_timeout_on_generic': '}, timeout, ThreadPool.Names.GENERIC);' in handshaker_text,
        'visible_transport_source_has_configureBlocking_call': 'configureBlocking(' in tcp_text or 'configureBlocking(' in ts_text or 'configureBlocking(' in handshaker_text,
        'visible_transport_source_has_socketchannel_read_call': 'SocketChannel.read(' in tcp_text or 'SocketChannel.read(' in ts_text or 'SocketChannel.read(' in handshaker_text,
    }

    if (
        generic_count > transport_count
        and result['tcptransport_wraps_open_connection_listener_on_generic']
        and result['transportservice_handshake_response_handler_on_generic']
        and not result['visible_transport_source_has_configureBlocking_call']
        and not result['visible_transport_source_has_socketchannel_read_call']
    ):
        result['checker_result'] = (
            'artifact_shows_main_same_socket_payload_reads_on_opensearch_generic_threads_but_visible_transport_source_only_exposes_generic_post_read_dispatch_not_a_direct_generic_socket_read_callsite'
        )
    else:
        result['checker_result'] = 'generic_payload_path_vs_transport_source_did_not_reach_expected_narrowing'

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write('\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
