#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_discovery_roster_absence_matches_listener_drop_after_local_probe.py "
            "<transport-connect.json> <transport-handshake.json> <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    connect = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    handshake = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    stdout = Path(sys.argv[3]).read_text(encoding="utf-8", errors="replace")

    local_tcp_connected = connect.get("tcp_connected") is True
    local_handshake_ok = (
        handshake.get("tcp_connected") is True
        and handshake.get("response_received") is True
        and handshake.get("response_starts_with_es") is True
    )
    open_request = stdout.count("steelsearch_open_connection_stage=request")
    open_response = stdout.count("steelsearch_open_connection_stage=response")
    open_failure = stdout.count("steelsearch_open_connection_stage=failure")
    connect_refused = stdout.count("Connection refused: /127.0.0.1:39517")
    cluster_not_discovered = stdout.count("cluster-manager not discovered yet")

    print(f"local_tcp_connected={local_tcp_connected}")
    print(f"local_handshake_ok={local_handshake_ok}")
    print(f"open_request={open_request}")
    print(f"open_response={open_response}")
    print(f"open_failure={open_failure}")
    print(f"connect_refused={connect_refused}")
    print(f"cluster_not_discovered={cluster_not_discovered}")

    if (
        local_tcp_connected
        and local_handshake_ok
        and open_request > 0
        and open_response == 0
        and open_failure == open_request
        and connect_refused > 0
        and cluster_not_discovered > 0
    ):
        print(
            "checker_result=java_discovery_roster_absence_matches_rust_listener_becoming_refused_after_local_probe_success"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
