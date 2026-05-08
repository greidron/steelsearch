#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_selector_ready_absence_more_likely_than_close_before_doReadBytes.py "
            "<abstract-nio-byte-unsafe-javap.txt> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    read_loop = Path(sys.argv[1]).read_text(errors="replace")
    stdout = Path(sys.argv[2]).read_text(errors="replace")

    has_should_break = "Method io/netty/channel/nio/AbstractNioByteChannel.shouldBreakReadReady" in read_loop
    has_clear_read_pending_then_return = "Method io/netty/channel/nio/AbstractNioByteChannel.clearReadPending" in read_loop
    has_do_read_bytes = "Method io/netty/channel/nio/AbstractNioByteChannel.doReadBytes" in read_loop
    has_fire_channel_read = "InterfaceMethod io/netty/channel/ChannelPipeline.fireChannelRead" in read_loop
    has_fire_read_complete = "InterfaceMethod io/netty/channel/ChannelPipeline.fireChannelReadComplete" in read_loop

    write_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
            r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
            stdout,
        )
    }
    read_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_message_channel_stage=channel_read .*?local=/127\.0\.0\.1:(\d+)",
            stdout,
        )
    }
    close_future = stdout.count("steelsearch_netty4_tcpchannel_stage=close_future_listener")

    print(f"has_should_break={has_should_break}")
    print(f"has_clear_read_pending_then_return={has_clear_read_pending_then_return}")
    print(f"has_do_read_bytes={has_do_read_bytes}")
    print(f"has_fire_channel_read={has_fire_channel_read}")
    print(f"has_fire_read_complete={has_fire_read_complete}")
    print(f"write_ports={len(write_ports)}")
    print(f"read_ports={len(read_ports)}")
    print(f"write_read_overlap={len(write_ports & read_ports)}")
    print(f"close_future={close_future}")

    if (
        has_should_break
        and has_clear_read_pending_then_return
        and has_do_read_bytes
        and has_fire_channel_read
        and has_fire_read_complete
        and len(write_ports) > 0
        and len(write_ports & read_ports) == 0
        and close_future >= len(write_ports)
    ):
        print(
            "checker_result="
            "given_read_loop_contract_and_zero_same_socket_channelRead_"
            "missing_selector_ready_is_more_likely_than_close_before_doReadBytes"
        )
        return 0

    print("checker_result=inconclusive_or_different_read_loop_boundary")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
