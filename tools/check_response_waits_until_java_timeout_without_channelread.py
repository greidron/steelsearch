#!/usr/bin/env python3
import json
import re
import statistics
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_response_waits_until_java_timeout_without_channelread.py "
            "<opensearch-stdout.log> <transport-seed-capture.json>",
            file=sys.stderr,
        )
        return 2

    stdout = Path(sys.argv[1]).read_text(errors="replace")
    capture = json.loads(Path(sys.argv[2]).read_text())

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
    explicit_local_close = stdout.count("hint=explicitLocalClose")

    deltas = []
    for entry in capture:
        first_frame = entry.get("first_frame") or {}
        if first_frame.get("action_hint") != "internal:tcp/handshake":
            continue
        if entry.get("response_frame") is None:
            continue
        sent = entry.get("response_frame_sent_at_ms")
        end = entry.get("connection_end_at_ms")
        if sent is None or end is None:
            continue
        deltas.append(end - sent)

    print(f"write_ports={len(write_ports)}")
    print(f"read_ports={len(read_ports)}")
    print(f"write_read_overlap={len(write_ports & read_ports)}")
    print(f"handshake_timeout={handshake_timeout}")
    print(f"explicit_local_close={explicit_local_close}")
    print(f"response_delta_count={len(deltas)}")
    print(f"response_delta_min_ms={min(deltas) if deltas else None}")
    print(f"response_delta_median_ms={statistics.median(deltas) if deltas else None}")
    print(f"response_delta_max_ms={max(deltas) if deltas else None}")

    if (
        len(write_ports) > 0
        and len(write_ports & read_ports) == 0
        and handshake_timeout > 0
        and explicit_local_close >= handshake_timeout
        and len(deltas) >= handshake_timeout
        and statistics.median(deltas) >= 900
    ):
        print(
            "checker_result="
            "rust_response_waits_on_socket_until_java_1s_timeout_local_close_"
            "without_any_same_socket_channelRead"
        )
        return 0

    print("checker_result=inconclusive_or_different_timing")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
