#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def count(path):
    text = Path(path).read_text(encoding='utf-8', errors='ignore')
    return {
        'transport_worker_samples': text.count('[transport_worker]'),
        'ioutil_read_into_native_buffer_samples': text.count('sun/nio/ch/IOUtil.readIntoNativeBuffer'),
        'socket_dispatcher_read_samples': text.count('sun/nio/ch/SocketDispatcher.read'),
        'socket_dispatcher_read0_samples': text.count('SocketDispatcher.read0'),
        'unix_file_dispatcher_read0_samples': text.count('UnixFileDispatcherImpl.read0'),
        'ioutil_read_samples': text.count('sun/nio/ch/IOUtil.read'),
        'nio_socket_channel_doReadBytes_samples': text.count('io/netty/channel/socket/nio/NioSocketChannel.doReadBytes'),
        'nio_byte_unsafe_read_samples': text.count('io/netty/channel/nio/AbstractNioByteChannel$NioByteUnsafe.read'),
    }


def main():
    if len(sys.argv) != 3:
        print('usage: check_mid_wrapper_read_candidates.py <readIntoNativeBuffer-collapsed> <SocketDispatcher.read-collapsed>')
        return 2
    a = count(sys.argv[1])
    b = count(sys.argv[2])
    result = {
        'read_into_native_buffer': a,
        'socket_dispatcher_read': b,
    }
    if a['ioutil_read_into_native_buffer_samples'] > 0 or b['socket_dispatcher_read_samples'] > 0:
        result['checker_result'] = 'mid_wrapper_candidates_capture_pre_read0_boundary'
    else:
        result['checker_result'] = 'mid_wrapper_candidates_did_not_capture_pre_read0_boundary'
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
