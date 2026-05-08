#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_response_flush_stops_before_java_channel_read.py "
            "<rust-stderr.log> <opensearch-stdout.log> <transport-seed-capture.json>",
            file=sys.stderr,
        )
        return 2

    rust_stderr = Path(sys.argv[1]).read_text(errors="replace")
    java_stdout = Path(sys.argv[2]).read_text(errors="replace")
    capture = json.loads(Path(sys.argv[3]).read_text())

    rust_before_write = rust_stderr.count("steelsearch_tcp_handshake_response_stage=before_write")
    rust_after_write = rust_stderr.count("steelsearch_tcp_handshake_response_stage=after_write")
    rust_after_flush = rust_stderr.count("steelsearch_tcp_handshake_response_stage=after_flush")

    response_frames = sum(
        1
        for entry in capture
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:tcp/handshake" and entry.get("response_frame")
    )

    write_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_tcpchannel_stage=before_write_and_flush "
            r".*?local=/127\.0\.0\.1:(\d+) remote=/127\.0\.0\.1:\d+ bytesLength=55",
            java_stdout,
        )
    }
    read_ports = {
        int(m.group(1))
        for m in re.finditer(
            r"steelsearch_netty4_message_channel_stage=channel_read "
            r".*?local=/127\.0\.0\.1:(\d+)",
            java_stdout,
        )
    }

    response_read = java_stdout.count("steelsearch_transport_handshaker_stage=response_read")
    handle_response = java_stdout.count("steelsearch_transport_handshaker_stage=handle_response")
    handshake_timeout = java_stdout.count("handshake_timeout[1s]")

    print(f"rust_before_write={rust_before_write}")
    print(f"rust_after_write={rust_after_write}")
    print(f"rust_after_flush={rust_after_flush}")
    print(f"response_frames={response_frames}")
    print(f"java_write_ports={len(write_ports)}")
    print(f"java_read_ports={len(read_ports)}")
    print(f"java_write_read_overlap={len(write_ports & read_ports)}")
    print(f"java_response_read={response_read}")
    print(f"java_handle_response={handle_response}")
    print(f"java_handshake_timeout={handshake_timeout}")

    if (
        rust_after_flush > 0
        and response_frames >= rust_after_flush - 1
        and len(write_ports) > 0
        and len(write_ports & read_ports) == 0
        and response_read == 0
        and handle_response == 0
        and handshake_timeout > 0
    ):
        print(
            "checker_result="
            "rust_flush_and_capture_complete_but_java_same_socket_never_reaches_channelRead_"
            "so_direct_boundary_is_before_netty_message_handler_dispatch"
        )
        return 0

    print("checker_result=inconclusive_or_different_boundary")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
