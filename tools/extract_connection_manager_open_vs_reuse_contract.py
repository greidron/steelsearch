#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'error': 'usage: extract_connection_manager_open_vs_reuse_contract.py <ClusterConnectionManager.java>'}))
        return 1
    text = Path(sys.argv[1]).read_text()
    result = {
        'open_connection_calls_internal_open_connection': 'openConnection(DiscoveryNode node, ConnectionProfile connectionProfile, ActionListener<Transport.Connection> listener)' in text and 'internalOpenConnection(node, resolvedProfile, listener);' in text,
        'connect_to_node_registers_connected_nodes': 'connectedNodes.putIfAbsent(node, conn)' in text,
        'get_connection_uses_connected_nodes': 'Transport.Connection connection = connectedNodes.get(node);' in text,
        'node_connected_depends_on_connected_nodes': 'return connectedNodes.containsKey(node);' in text,
    }
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
