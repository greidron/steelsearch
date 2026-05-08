#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def ports(pattern: str, text: str) -> set[int]:
    return {int(m.group(1)) for m in re.finditer(pattern, text)}


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_same_socket_close_future_before_message_handler.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    stdout = Path(sys.argv[1]).read_text(errors="replace")

    write_ports = ports(
        r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
        r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
        stdout,
    )
    close_future_ports = ports(
        r"steelsearch_netty4_tcpchannel_stage=close_future_listener "
        r"local=/127\.0\.0\.1:(\d+)",
        stdout,
    )
    close_trace_ports = ports(
        r"steelsearch_netty4_tcpchannel_stage=close_trace_emit "
        r"local=/127\.0\.0\.1:(\d+)",
        stdout,
    )
    read_ports = ports(
        r"steelsearch_netty4_message_channel_stage=channel_read "
        r".*?local=/127\.0\.0\.1:(\d+)",
        stdout,
    )
    inactive_ports = ports(
        r"steelsearch_netty4_message_channel_stage=channel_inactive "
        r".*?local=/127\.0\.0\.1:(\d+)",
        stdout,
    )

    write_close_future_overlap = write_ports & close_future_ports
    write_close_trace_overlap = write_ports & close_trace_ports
    write_read_overlap = write_ports & read_ports
    write_inactive_overlap = write_ports & inactive_ports

    print(f"write_ports={len(write_ports)}")
    print(f"close_future_ports={len(close_future_ports)}")
    print(f"close_trace_ports={len(close_trace_ports)}")
    print(f"write_close_future_overlap={len(write_close_future_overlap)}")
    print(f"write_close_trace_overlap={len(write_close_trace_overlap)}")
    print(f"write_read_overlap={len(write_read_overlap)}")
    print(f"write_inactive_overlap={len(write_inactive_overlap)}")
    print(f"write_only_without_close_future={sorted(write_ports - close_future_ports)[:20]}")

    if not write_ports:
        print("checker_result=inconclusive_no_low_level_handshake_write_ports")
        return 1

    if (
        len(write_close_future_overlap) >= max(1, len(write_ports) - 2)
        and len(write_read_overlap) == 0
        and len(write_inactive_overlap) == 0
    ):
        print(
            "checker_result="
            "same_socket_close_future_fires_before_any_message_handler_readside_events"
        )
        return 0

    print("checker_result=inconclusive_or_mixed_close_future_boundary")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
