#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path

CLOSE_RE = re.compile(r"steelsearch_netty4_tcpchannel_stage=close_trace_emit local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:(\d+) hint=([A-Za-z]+)")
TIMEOUT_RE = re.compile(r"handshake_timeout\[1s\]")


def parse_ports(stdout: str):
    explicit = set()
    unknown = set()
    for line in stdout.splitlines():
        m = CLOSE_RE.search(line)
        if not m:
            continue
        local = int(m.group(1))
        hint = m.group(3)
        if hint == 'explicitLocalClose':
            explicit.add(local)
        elif hint == 'unknown':
            unknown.add(local)
    return explicit, unknown


def parse_remote_eof_ports(captures):
    ports = set()
    for capture in captures:
        first = capture.get('first_frame') or {}
        if first.get('action_hint') != 'internal:tcp/handshake':
            continue
        if capture.get('first_post_response_event') != 'remote_eof':
            continue
        peer = capture.get('peer_addr', '')
        if ':' in peer:
            ports.add(int(peer.rsplit(':', 1)[1]))
    return ports


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_fresh_formed_only_remote_eof_vs_java_close.py STDOUT CAPTURE')
    stdout = Path(sys.argv[1]).read_text(encoding='utf-8', errors='replace')
    captures = json.loads(Path(sys.argv[2]).read_text(encoding='utf-8'))
    explicit, unknown = parse_ports(stdout)
    remote_eof_ports = parse_remote_eof_ports(captures)
    overlap_explicit = sorted(remote_eof_ports & explicit)
    overlap_unknown = sorted(remote_eof_ports & unknown)
    result = 'inconclusive'
    if overlap_explicit and len(overlap_explicit) >= max(1, len(remote_eof_ports) // 2):
        result = 'fresh_formed_only_failure_points_more_directly_to_java_explicitLocalClose_than_rust_hold_open_lifecycle'
    print(json.dumps({
        'remote_eof_port_count': len(remote_eof_ports),
        'explicit_local_close_port_count': len(explicit),
        'unknown_close_port_count': len(unknown),
        'remote_eof_explicit_overlap_count': len(overlap_explicit),
        'remote_eof_unknown_overlap_count': len(overlap_unknown),
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
