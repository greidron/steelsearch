#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_hidden_alias_not_persisted_in_steelsearch_state.py <canonical_aliases.json> <gateway-state.json> <production-membership.json>')

    canonical = load(sys.argv[1])
    gateway = load(sys.argv[2])
    membership = load(sys.argv[3])

    canonical_only_one_rust_address = (
        canonical.get('result')
        == 'cluster_state_additional_aliases_do_not_appear_as_distinct_rust_transport_addresses_in_logs_and_instead_share_one_canonical_rust_address'
        and canonical.get('unique_canonical_rust_address_count') == 1
    )

    gateway_nodes = ((gateway.get('cluster_state') or {}).get('nodes') or [])
    gateway_rust_addresses = sorted({n.get('transport_address') for n in gateway_nodes if n.get('node_id') == 'rust-replica-1'})
    membership_has_no_transport_addresses = all('transport_address' not in v for v in (membership.get('members') or {}).values())

    result = (
        'hidden_alias_is_not_persisted_in_steelsearch_gateway_or_membership_state_and_remains_transient_peerfinder_side_keying'
        if canonical_only_one_rust_address and gateway_rust_addresses == ['127.0.0.1:38113'] and membership_has_no_transport_addresses
        else 'hidden_alias_persistence_boundary_not_fully_established'
    )

    print(json.dumps({
        'canonical_only_one_rust_address': canonical_only_one_rust_address,
        'gateway_rust_addresses': gateway_rust_addresses,
        'membership_has_no_transport_addresses': membership_has_no_transport_addresses,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
