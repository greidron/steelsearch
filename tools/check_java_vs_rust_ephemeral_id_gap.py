#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({'error': 'usage: check_java_vs_rust_ephemeral_id_gap.py <rust_identity_contract.json> <mixed_report.json>'}))
        return 1
    rust = load(sys.argv[1])
    report = load(sys.argv[2])
    seed = report.get('seed_peer_identity', {}).get('discovery_node', {})
    java_has_distinct_ephemeral = bool(seed.get('id')) and bool(seed.get('ephemeral_id')) and seed.get('id') != seed.get('ephemeral_id')
    rust_reuses = bool(rust.get('transport_identity_response_reuses_node_id_as_ephemeral_id'))

    if java_has_distinct_ephemeral and rust_reuses:
        result = 'rust_transport_identity_reuses_node_id_as_ephemeral_id_unlike_java_reference'
    elif not java_has_distinct_ephemeral:
        result = 'java_reference_ephemeral_id_distinction_not_observed'
    else:
        result = 'rust_identity_ephemeral_gap_not_detected'

    print(json.dumps({
        'java_reference_has_distinct_ephemeral_id': java_has_distinct_ephemeral,
        'rust_reuses_node_id_as_ephemeral_id': rust_reuses,
        'result': result,
    }))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
