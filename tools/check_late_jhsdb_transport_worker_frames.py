#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

THREAD_START = re.compile(r'^"(?P<name>.+?)".* nid=(?:0x(?P<nid_hex>[0-9a-f]+)|(?P<nid_dec>\d+))', re.I)


def parse_blocks(text):
    blocks = {}
    current_tid = None
    current = []
    for line in text.splitlines():
        m = THREAD_START.match(line.strip())
        if m:
            if current_tid is not None:
                blocks[current_tid] = '\n'.join(current)
            if m.group('nid_hex'):
                current_tid = int(m.group('nid_hex'), 16)
            else:
                current_tid = int(m.group('nid_dec'))
            current = [line]
        elif current_tid is not None:
            current.append(line)
    if current_tid is not None:
        blocks[current_tid] = '\n'.join(current)
    return blocks


def main():
    if len(sys.argv) != 3:
        print('usage: check_late_jhsdb_transport_worker_frames.py <late-strace.log> <jhsdb-jstack.txt>')
        return 2
    strace_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
    jhsdb_text = Path(sys.argv[2]).read_text(encoding='utf-8', errors='ignore')

    tids = sorted(set(int(m.group(1)) for m in re.finditer(r'^\s*(\d+).*TCPv6', strace_text, re.M)))
    blocks = parse_blocks(jhsdb_text)

    frames = {}
    for tid in tids:
        block = blocks.get(tid, '')
        frames[str(tid)] = {
            'transport_worker': '[transport_worker]' in block,
            'epoll_wait': 'sun.nio.ch.EPoll.wait' in block,
            'selector_doSelect': 'sun.nio.ch.EPollSelectorImpl.doSelect' in block,
            'nio_io_handler_select': 'io.netty.channel.nio.NioIoHandler.select' in block,
            'nio_io_handler_run': 'io.netty.channel.nio.NioIoHandler.run' in block,
            'single_thread_io_event_loop': 'io.netty.channel.SingleThreadIoEventLoop.runIo' in block,
            'unix_file_dispatcher_read0': 'UnixFileDispatcherImpl.read0' in block,
            'socket_dispatcher_read0': 'SocketDispatcher.read0' in block,
        }

    result = 'undetermined'
    if tids and all(v['transport_worker'] and v['epoll_wait'] and v['nio_io_handler_select'] and v['nio_io_handler_run'] for v in frames.values()):
        result = 'late_jhsdb_mixed_stack_places_same_socket_transport_worker_tids_in_epoll_wait_to_NioIoHandler_select_run_path'

    print(json.dumps({
        'checker_result': result,
        'same_socket_tcp_tids': tids,
        'frame_facts': frames,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
