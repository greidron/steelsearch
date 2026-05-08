#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_configured_host_plus_cluster_state_additions.py <single_remote_seed_candidate.json> <multiple_address_keyed_peers.json> <cluster_state_contribution.json>')

    single_seed = load(sys.argv[1])
    multiple_peers = load(sys.argv[2])
    cluster_state = load(sys.argv[3])

    configured_hosts_base_one = (
        single_seed.get('result')
        == 'mixed_probe_has_two_seed_hosts_but_peerfinder_skips_local_one_so_probe_triggers_collapse_to_single_remote_seed_candidate'
    )
    same_round_request_peers_count = multiple_peers.get('same_round_request_peers_count', 0)
    cluster_state_must_contribute = (
        cluster_state.get('result')
        == 'configured_hosts_alone_cannot_explain_alias_multiplicity_so_cluster_state_cluster_manager_nodes_must_contribute'
    )

    cluster_state_additional_count_lower_bound = max(0, same_round_request_peers_count - 1)

    result = (
        'alias_multiplicity_best_matches_configured_host_base_one_plus_cluster_state_additional_entries'
        if configured_hosts_base_one and cluster_state_must_contribute and same_round_request_peers_count >= 3
        else 'configured_host_plus_cluster_state_additions_not_fully_established'
    )

    print(json.dumps({
        'configured_hosts_base_one': configured_hosts_base_one,
        'same_round_request_peers_count': same_round_request_peers_count,
        'cluster_state_must_contribute': cluster_state_must_contribute,
        'cluster_state_additional_count_lower_bound': cluster_state_additional_count_lower_bound,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
