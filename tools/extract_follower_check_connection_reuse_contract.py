#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: extract_follower_check_connection_reuse_contract.py "
            "<FollowersChecker.java> <TransportService.java> <TcpTransport.java>",
            file=sys.stderr,
        )
        return 2

    followers_checker = Path(sys.argv[1]).read_text(encoding="utf-8")
    transport_service = Path(sys.argv[2]).read_text(encoding="utf-8")
    tcp_transport = Path(sys.argv[3]).read_text(encoding="utf-8")

    result = {
        "followers_checker_uses_transport_service_send_request": "transportService.sendRequest(" in followers_checker,
        "followers_checker_requests_type_ping": ".withType(Type.PING)" in followers_checker,
        "transport_service_send_request_uses_get_connection": "connection = getConnection(node);" in transport_service,
        "transport_service_get_connection_uses_connection_manager": "return connectionManager.getConnection(node);" in transport_service,
        "tcp_transport_node_channels_route_by_request_type": "TcpChannel channel = channel(options.type());" in tcp_transport,
        "tcp_transport_has_dedicated_type_channel_lookup": "ConnectionProfile.ConnectionTypeHandle connectionTypeHandle = typeMapping.get(type);" in tcp_transport,
    }
    print(json.dumps(result, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
