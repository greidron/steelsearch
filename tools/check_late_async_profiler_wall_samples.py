#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        print('usage: check_late_async_profiler_wall_samples.py <collapsed-file>')
        return 2
    text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
    result = {
        'transport_worker_samples': text.count('[transport_worker]'),
        'epoll_wait_samples': text.count('sun/nio/ch/EPoll.wait'),
        'selector_doSelect_samples': text.count('sun/nio/ch/EPollSelectorImpl.doSelect'),
        'nio_io_handler_select_samples': text.count('io/netty/channel/nio/NioIoHandler.select'),
        'unix_file_dispatcher_read0_samples': text.count('UnixFileDispatcherImpl.read0'),
        'socket_dispatcher_read0_samples': text.count('SocketDispatcher.read0'),
        'nio_socket_channel_doReadBytes_samples': text.count('NioSocketChannel.doReadBytes'),
        'nio_byte_unsafe_read_samples': text.count('AbstractNioByteChannel$NioByteUnsafe.read'),
    }
    checker = 'undetermined'
    if result['transport_worker_samples'] > 0:
        checker = 'late_async_profiler_wall_captures_transport_worker_samples'
        if result['unix_file_dispatcher_read0_samples'] > 0 or result['socket_dispatcher_read0_samples'] > 0 or result['nio_socket_channel_doReadBytes_samples'] > 0 or result['nio_byte_unsafe_read_samples'] > 0:
            checker = 'late_async_profiler_wall_captures_transport_worker_read_side_frames'
    print(json.dumps({'checker_result': checker, **result}, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
