#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_cluster_state_aliases_share_canonical_rust_address.py <cluster_state_contribution.json> <opensearch_stdout.log>')

    cluster_state = load(sys.argv[1])
    log_text = Path(sys.argv[2]).read_text()

    cluster_state_must_contribute = (
        cluster_state.get('result')
        == 'configured_hosts_alone_cannot_explain_alias_multiplicity_so_cluster_state_cluster_manager_nodes_must_contribute'
    )

    addresses = sorted(set(re.findall(r'\{rust-replica-1\}\{rust-replica-1\}\{rust-replica-1-ephemeral\}\{127\.0\.0\.1\}\{(127\.0\.0\.1:\d+)\}', log_text)))
    unique_canonical_rust_address_count = len(addresses)

    result = (
        'cluster_state_additional_aliases_do_not_appear_as_distinct_rust_transport_addresses_in_logs_and_instead_share_one_canonical_rust_address'
        if cluster_state_must_contribute and unique_canonical_rust_address_count == 1
        else 'cluster_state_alias_canonical_rust_address_not_fully_established'
    )

    print(json.dumps({
        'cluster_state_must_contribute': cluster_state_must_contribute,
        'unique_canonical_rust_addresses': addresses,
        'unique_canonical_rust_address_count': unique_canonical_rust_address_count,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
