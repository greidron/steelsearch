#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_higher_wrapper_read_candidate.py <collapsed-file>')
        return 2
    text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
    result = {
        'transport_worker_samples': text.count('[transport_worker]'),
        'ioutil_read_samples': text.count('sun/nio/ch/IOUtil.read'),
        'socket_dispatcher_read0_samples': text.count('SocketDispatcher.read0'),
        'unix_file_dispatcher_read0_samples': text.count('UnixFileDispatcherImpl.read0'),
        'nio_socket_channel_doReadBytes_samples': text.count('io/netty/channel/socket/nio/NioSocketChannel.doReadBytes'),
        'nio_byte_unsafe_read_samples': text.count('io/netty/channel/nio/AbstractNioByteChannel$NioByteUnsafe.read'),
    }
    checker = 'undetermined'
    if result['ioutil_read_samples'] > 0:
        checker = 'higher_wrapper_ioutil_read_candidate_captures_read_wrapper_samples'
        if result['socket_dispatcher_read0_samples'] > 0 or result['unix_file_dispatcher_read0_samples'] > 0:
            checker = 'higher_wrapper_ioutil_read_candidate_reaches_native_wrapper_boundary'
    print(json.dumps({'checker_result': checker, **result}, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
