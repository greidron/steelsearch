#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def ports(pattern: str, text: str) -> set[int]:
    return {int(m.group(1)) for m in re.finditer(pattern, text)}


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_same_socket_read_lifecycle_closes_before_decoder.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    stdout = Path(sys.argv[1]).read_text(errors="replace")

    write_ports = ports(
        r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
        r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
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
    exception_ports = ports(
        r"steelsearch_netty4_message_channel_stage=exception_caught "
        r".*?local=/127\.0\.0\.1:(\d+)",
        stdout,
    )

    read_overlap = write_ports & read_ports
    inactive_overlap = write_ports & inactive_ports
    exception_overlap = write_ports & exception_ports

    print(f"write_ports={len(write_ports)}")
    print(f"read_ports={len(read_ports)}")
    print(f"inactive_ports={len(inactive_ports)}")
    print(f"exception_ports={len(exception_ports)}")
    print(f"write_read_overlap={len(read_overlap)}")
    print(f"write_inactive_overlap={len(inactive_overlap)}")
    print(f"write_exception_overlap={len(exception_overlap)}")
    print(f"write_only_ports={sorted(write_ports - read_ports)[:20]}")

    if not write_ports:
        print("checker_result=inconclusive_no_low_level_handshake_write_ports")
        return 1

    if len(read_overlap) == 0 and len(inactive_overlap) == 0 and len(exception_overlap) == 0:
        print(
            "checker_result="
            "same_socket_never_reaches_message_handler_read_inactive_or_exception_events"
        )
        return 0

    if len(read_overlap) == 0 and len(inactive_overlap) >= max(1, len(write_ports) - 2):
        print(
            "checker_result="
            "same_socket_read_lifecycle_closes_or_inactivates_before_any_decoder_entry"
        )
        return 0

    print("checker_result=inconclusive_or_mixed_read_lifecycle")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
