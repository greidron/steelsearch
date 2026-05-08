#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: extract_connection_manager_registration_boundary.py <ClusterConnectionManager.java>"}))
        return 1

    text = Path(sys.argv[1]).read_text()
    result = {
        "connect_to_node_uses_connection_validator": "connectionValidator.validate(conn, resolvedProfile" in text,
        "validator_success_registers_connected_node": "connectedNodes.putIfAbsent(node, conn)" in text,
        "registration_triggers_on_node_connected": "connectionListener.onNodeConnected(node, conn)" in text,
        "get_connection_reads_connected_nodes": "Transport.Connection connection = connectedNodes.get(node);" in text,
        "node_connected_checks_connected_nodes": "return connectedNodes.containsKey(node);" in text,
        "close_listener_unregisters_connected_node": "connectedNodes.remove(node, finalConnection);" in text,
    }
    print(json.dumps(result))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
