#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_netty_read_loop_contract_points_before_fireChannelRead.py "
            "<abstract-nio-byte-unsafe-javap.txt> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    javap = Path(sys.argv[1]).read_text(errors="replace")
    stdout = Path(sys.argv[2]).read_text(errors="replace")

    source_has_do_read_bytes = "AbstractNioByteChannel.doReadBytes" in javap
    source_has_fire_channel_read = "ChannelPipeline.fireChannelRead" in javap
    source_has_fire_read_complete = "ChannelPipeline.fireChannelReadComplete" in javap

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

    handshake_timeout = stdout.count("handshake_timeout[1s]")
    close_future = stdout.count("steelsearch_netty4_tcpchannel_stage=close_future_listener")

    print(f"source_has_do_read_bytes={source_has_do_read_bytes}")
    print(f"source_has_fire_channel_read={source_has_fire_channel_read}")
    print(f"source_has_fire_read_complete={source_has_fire_read_complete}")
    print(f"write_ports={len(write_ports)}")
    print(f"read_ports={len(read_ports)}")
    print(f"write_read_overlap={len(write_ports & read_ports)}")
    print(f"handshake_timeout={handshake_timeout}")
    print(f"close_future={close_future}")

    if (
        source_has_do_read_bytes
        and source_has_fire_channel_read
        and source_has_fire_read_complete
        and len(write_ports) > 0
        and len(write_ports & read_ports) == 0
        and handshake_timeout > 0
        and close_future >= handshake_timeout
    ):
        print(
            "checker_result="
            "netty_read_loop_contract_would_fireChannelRead_after_doReadBytes_"
            "so_current_boundary_is_before_selector_read_loop_delivers_bytes"
        )
        return 0

    print("checker_result=inconclusive_or_different_contract")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
