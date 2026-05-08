#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_transport_open_stops_before_channels_opened.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    delegate_to_connection_manager = text.count("steelsearch_transport_open_stage=delegate_to_connection_manager")
    tcp_open_enter = text.count("steelsearch_tcp_open_stage=openConnection_enter")
    channels_opened = text.count("steelsearch_tcp_open_stage=channels_opened")
    listeners_attached = text.count("steelsearch_tcp_open_stage=connect_listeners_attached")
    timeout_scheduled = text.count("steelsearch_tcp_open_stage=connect_timeout_scheduled")

    print(f"delegate_to_connection_manager={delegate_to_connection_manager}")
    print(f"tcp_open_enter={tcp_open_enter}")
    print(f"channels_opened={channels_opened}")
    print(f"listeners_attached={listeners_attached}")
    print(f"timeout_scheduled={timeout_scheduled}")

    if delegate_to_connection_manager > 0 and tcp_open_enter > 0 and channels_opened == 0:
        print("checker_result=transport_open_stops_before_initiateConnection_finishes_opening_channels")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
