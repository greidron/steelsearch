#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_high_level_phase_blocked_before_open_connection_response.py "
            "<HandshakingTransportAddressConnector.java> <TcpTransport.java> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    connector_source = Path(sys.argv[1]).read_text(encoding="utf-8")
    tcp_source = Path(sys.argv[2]).read_text(encoding="utf-8")
    stdout = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")

    connector_high_level_inside_open_response = (
        "steelsearch_open_connection_stage=response" in connector_source
        and "steelsearch_probe_stage=start_high_level_handshake" in connector_source
        and "transportService.handshake(connection" in connector_source
    )
    tcp_executes_handshake_before_connection_publish = (
        "steelsearch_tcp_open_stage=channels_connected_listener_onResponse" in tcp_source
        and "executeHandshake(node, handshakeChannel, connectionProfile" in tcp_source
    )

    channels_connected_on_response = stdout.count("steelsearch_tcp_open_stage=channels_connected_listener_onResponse")
    open_response = stdout.count("steelsearch_open_connection_stage=response")
    open_failure = stdout.count("steelsearch_open_connection_stage=failure")
    start_high_level_handshake = stdout.count("steelsearch_probe_stage=start_high_level_handshake")
    transport_handshake_send_meta = stdout.count("action=internal:transport/handshake")
    tcp_handshake_send_meta = stdout.count("action=internal:tcp/handshake")

    print(f"connector_high_level_inside_open_response={connector_high_level_inside_open_response}")
    print(f"tcp_executes_handshake_before_connection_publish={tcp_executes_handshake_before_connection_publish}")
    print(f"channels_connected_on_response={channels_connected_on_response}")
    print(f"open_response={open_response}")
    print(f"open_failure={open_failure}")
    print(f"start_high_level_handshake={start_high_level_handshake}")
    print(f"transport_handshake_send_meta={transport_handshake_send_meta}")
    print(f"tcp_handshake_send_meta={tcp_handshake_send_meta}")

    if (
        connector_high_level_inside_open_response
        and tcp_executes_handshake_before_connection_publish
        and channels_connected_on_response > 0
        and open_response == 0
        and open_failure > 0
        and start_high_level_handshake == 0
        and transport_handshake_send_meta == 0
        and tcp_handshake_send_meta > 0
    ):
        print(
            "checker_result=java_discovery_never_reaches_transportservice_high_level_handshake_because_tcptransport_is_stuck_in_low_level_tcp_handshake_before_open_connection_response"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
