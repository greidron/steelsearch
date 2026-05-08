#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_transport_open_reaches_tcp_listener_boundary.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    delegate_to_connection_manager = text.count("steelsearch_transport_open_stage=delegate_to_connection_manager")
    tcp_open_enter = text.count("steelsearch_tcp_open_stage=openConnection_enter")
    channels_opened = text.count("steelsearch_tcp_open_stage=channels_opened")
    listeners_attached = text.count("steelsearch_tcp_open_stage=connect_listeners_attached")
    timeout_scheduled = text.count("steelsearch_tcp_open_stage=connect_timeout_scheduled")
    listener_onResponse = text.count("steelsearch_tcp_open_stage=channels_connected_listener_onResponse")
    listener_onFailure = text.count("steelsearch_tcp_open_stage=channels_connected_listener_onFailure")
    listener_onTimeout = text.count("steelsearch_tcp_open_stage=channels_connected_listener_onTimeout")

    print(f"delegate_to_connection_manager={delegate_to_connection_manager}")
    print(f"tcp_open_enter={tcp_open_enter}")
    print(f"channels_opened={channels_opened}")
    print(f"listeners_attached={listeners_attached}")
    print(f"timeout_scheduled={timeout_scheduled}")
    print(f"listener_onResponse={listener_onResponse}")
    print(f"listener_onFailure={listener_onFailure}")
    print(f"listener_onTimeout={listener_onTimeout}")

    if (
        delegate_to_connection_manager > 0
        and tcp_open_enter > 0
        and channels_opened > 0
        and listeners_attached > 0
        and timeout_scheduled > 0
        and listener_onResponse == 0
        and listener_onFailure == 0
    ):
        print("checker_result=transport_open_reaches_tcp_listener_attach_but_no_listener_callback_yet")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
