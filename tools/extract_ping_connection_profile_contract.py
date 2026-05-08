#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def extract(expr: str, text: str):
    m = re.search(expr, text, re.MULTILINE)
    return m.group(1) if m else None


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/home/ubuntu/OpenSearch")
    connection_profile = root / "server/src/main/java/org/opensearch/transport/ConnectionProfile.java"
    tcp_transport = root / "server/src/main/java/org/opensearch/transport/TcpTransport.java"

    cp_text = connection_profile.read_text(encoding="utf-8")
    tcp_text = tcp_transport.read_text(encoding="utf-8")

    ping_setting = extract(
        r"int connectionsPerNodePing = TransportSettings\.([A-Z0-9_]+)\.get\(settings\);",
        cp_text,
    )
    ping_bucket = "builder.addConnections(connectionsPerNodePing, TransportRequestOptions.Type.PING);" in cp_text
    ping_interval = extract(r"builder\.setPingInterval\(TransportSettings\.([A-Z0-9_]+)\.get\(settings\)\);", cp_text)
    ping_handle_lookup = "typeMapping.get(type)" in tcp_text and "TransportRequestOptions.Type" in tcp_text

    output = {
        "connection_profile_path": str(connection_profile),
        "tcp_transport_path": str(tcp_transport),
        "connections_per_node_ping_setting": ping_setting,
        "default_profile_has_dedicated_ping_bucket": ping_bucket,
        "ping_interval_setting": ping_interval,
        "tcp_transport_routes_type_via_handle_mapping": ping_handle_lookup,
    }
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
