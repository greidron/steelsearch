#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

HEADER_RE = re.compile(r'^"(?P<name>.+?)".* nid=(?:0x(?P<nid_hex>[0-9a-f]+)|(?P<nid_dec>\d+))', re.I)


def parse_same_socket_tids(strace_text):
    return sorted(set(int(m.group(1)) for m in re.finditer(r'^\s*(\d+).*TCPv6', strace_text, re.M)))


def split_blocks(text):
    blocks = {}
    current_tid = None
    current = []
    for line in text.splitlines():
        m = HEADER_RE.match(line.strip())
        if m:
            if current_tid is not None:
                blocks[current_tid] = '\n'.join(current)
            current_tid = int(m.group('nid_hex'), 16) if m.group('nid_hex') else int(m.group('nid_dec'))
            current = [line]
        elif current_tid is not None:
            current.append(line)
    if current_tid is not None:
        blocks[current_tid] = '\n'.join(current)
    return blocks


def main():
    if len(sys.argv) != 3:
        print('usage: check_repeated_jhsdb_exact_read_frames.py <late-strace.log> <jhsdb-dir>')
        return 2
    strace_text = Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')
    jhsdb_dir = Path(sys.argv[2])
    tids = parse_same_socket_tids(strace_text)
    hits = []
    for snap in sorted(jhsdb_dir.glob('*.txt')):
        blocks = split_blocks(snap.read_text(encoding='utf-8', errors='ignore'))
        for tid in tids:
            block = blocks.get(tid, '')
            if not block:
                continue
            if any(token in block for token in ['UnixFileDispatcherImpl.read0', 'SocketDispatcher.read0', 'NioSocketChannel.doReadBytes', 'AbstractNioByteChannel$NioByteUnsafe.read']):
                hits.append({
                    'snapshot': snap.name,
                    'tid': tid,
                    'unix_file_dispatcher_read0': 'UnixFileDispatcherImpl.read0' in block,
                    'socket_dispatcher_read0': 'SocketDispatcher.read0' in block,
                    'nio_socket_channel_doReadBytes': 'NioSocketChannel.doReadBytes' in block,
                    'nio_byte_unsafe_read': 'AbstractNioByteChannel$NioByteUnsafe.read' in block,
                })
    result = 'repeated_jhsdb_did_not_capture_exact_payload_read_frame' if not hits else 'repeated_jhsdb_captured_exact_payload_read_side_frames'
    print(json.dumps({
        'checker_result': result,
        'same_socket_tcp_tids': tids,
        'hits': hits,
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    raise SystemExit(main())
