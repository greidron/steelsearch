#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def count(text: str, needle: str) -> int:
    return text.count(needle)


def summarize(path: str) -> dict:
    text = Path(path).read_text(encoding='utf-8', errors='ignore')
    return {
        'transport_worker_samples': count(text, '[transport_worker]'),
        'socket_dispatcher_read_samples': count(text, 'sun/nio/ch/SocketDispatcher.read'),
        'socket_dispatcher_read0_samples': count(text, 'SocketDispatcher.read0'),
        'java_socket_dispatcher_read0_samples': count(text, 'Java_sun_nio_ch_SocketDispatcher_read0'),
        'ioutil_read_into_native_buffer_samples': count(text, 'sun/nio/ch/IOUtil.readIntoNativeBuffer'),
        'unix_file_dispatcher_read0_samples': count(text, 'UnixFileDispatcherImpl.read0'),
        'java_unix_file_dispatcher_read0_samples': count(text, 'Java_sun_nio_ch_UnixFileDispatcherImpl_read0'),
        'nio_socket_channel_doReadBytes_samples': count(text, 'io/netty/channel/socket/nio/NioSocketChannel.doReadBytes'),
        'nio_byte_unsafe_read_samples': count(text, 'io/netty/channel/nio/AbstractNioByteChannel$NioByteUnsafe.read'),
        'socket_token_samples': count(text, 'socket'),
        'read_token_samples': count(text, ';read'),
    }


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_pre_read0_native_transition_candidate.py <socket-read-collapsed> <read-into-native-collapsed>')
        return 2
    socket_read = summarize(sys.argv[1])
    read_into_native = summarize(sys.argv[2])
    result = {
        'socket_dispatcher_read_cstack': socket_read,
        'read_into_native_buffer_cstack': read_into_native,
    }
    native_hits = (
        socket_read['socket_dispatcher_read0_samples']
        + socket_read['java_socket_dispatcher_read0_samples']
        + socket_read['unix_file_dispatcher_read0_samples']
        + socket_read['java_unix_file_dispatcher_read0_samples']
        + read_into_native['socket_dispatcher_read0_samples']
        + read_into_native['java_socket_dispatcher_read0_samples']
        + read_into_native['unix_file_dispatcher_read0_samples']
        + read_into_native['java_unix_file_dispatcher_read0_samples']
    )
    if native_hits > 0:
        result['checker_result'] = 'cstack_method_candidates_reach_native_read0_transition'
    elif (
        socket_read['socket_dispatcher_read_samples'] > 0
        or read_into_native['ioutil_read_into_native_buffer_samples'] > 0
    ):
        result['checker_result'] = 'cstack_method_candidates_confirm_pre_read0_boundary_but_still_do_not_capture_read0_transition'
    else:
        result['checker_result'] = 'cstack_method_candidates_did_not_capture_pre_read0_or_read0_boundary'
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
