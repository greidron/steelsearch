#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({'error': 'usage: extract_rust_transport_identity_contract.py <main.rs>'}))
        return 1
    text = Path(sys.argv[1]).read_text()
    result = {
        'transport_identity_response_writes_node_id': 'write_string(&mut payload, &transport_identity.node_id);' in text,
        'transport_identity_response_reuses_node_id_as_ephemeral_id': text.count('write_string(&mut payload, &transport_identity.node_id);') >= 2,
        'publish_with_join_response_reuses_node_id_as_ephemeral_id': 'write_discovery_node_wire(\n            &mut payload,\n            &transport_identity.node_name,\n            &transport_identity.node_id,\n            &transport_identity.node_id,' in text,
    }
    print(json.dumps(result))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
