#!/usr/bin/env python3
import re
import sys
from pathlib import Path


TIMEOUT_BRANCH_RE = re.compile(
    r"steelsearch_tcp_open_stage=execute_handshake_failure_timeout_branch node=\{127\.0\.0\.1:(\d+)\}"
)
CLOSE_RE = re.compile(
    r"steelsearch_tcp_open_stage=close_and_fail_enter node=\{127\.0\.0\.1:(\d+)\}.*causeMessage=\[\]\[127\.0\.0\.1:\1\] handshake_timeout\[5s\]"
)
CHANNEL_READ_RE = re.compile(
    r"steelsearch_netty4_message_channel_stage=channel_read local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:(\d+)"
)


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_delayed_timeout_same_socket_no_channelread.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    timeout_ports = {int(m.group(1)) for m in TIMEOUT_BRANCH_RE.finditer(text)}
    close_ports = {int(m.group(1)) for m in CLOSE_RE.finditer(text)}
    read_local_ports = {int(m.group(1)) for m in CHANNEL_READ_RE.finditer(text)}
    read_remote_ports = {int(m.group(2)) for m in CHANNEL_READ_RE.finditer(text)}

    timeout_read_overlap = sorted(timeout_ports & read_local_ports)
    close_read_overlap = sorted(close_ports & read_local_ports)

    print(f"timeout_ports={len(timeout_ports)}")
    print(f"close_ports={len(close_ports)}")
    print(f"read_local_ports={len(read_local_ports)}")
    print(f"read_remote_ports={len(read_remote_ports)}")
    print(f"timeout_read_overlap={timeout_read_overlap}")
    print(f"close_read_overlap={close_read_overlap}")

    if timeout_ports and not timeout_read_overlap and not close_read_overlap:
        print("checker_result=delayed_timeout_same_socket_still_never_reaches_channelRead")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
