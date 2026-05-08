#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        raise SystemExit('usage: check_multiplicity_requires_cluster_state_contribution.py <single_remote_seed_candidate.json> <multiple_address_keyed_peers.json> <source_candidates.json>')

    single_seed = load(sys.argv[1])
    multiple_peers = load(sys.argv[2])
    candidates = load(sys.argv[3])

    configured_hosts_side_collapses_to_one_remote_candidate = (
        single_seed.get('result')
        == 'mixed_probe_has_two_seed_hosts_but_peerfinder_skips_local_one_so_probe_triggers_collapse_to_single_remote_seed_candidate'
    )
    artifact_has_alias_multiplicity = (
        multiple_peers.get('result')
        == 'multiple_address_keyed_peer_entries_can_persist_as_aliases_of_single_canonical_remote_node'
        and multiple_peers.get('same_round_request_peers_count', 0) >= 3
    )
    source_exposes_both_candidate_axes = (
        candidates.get('result')
        == 'current_mixed_probe_runtime_exposes_both_cluster_state_cluster_manager_nodes_and_configured_hosts_as_remaining_alias_entry_sources'
    )

    result = (
        'configured_hosts_alone_cannot_explain_alias_multiplicity_so_cluster_state_cluster_manager_nodes_must_contribute'
        if configured_hosts_side_collapses_to_one_remote_candidate
        and artifact_has_alias_multiplicity
        and source_exposes_both_candidate_axes
        else 'cluster_state_contribution_to_alias_multiplicity_not_fully_established'
    )

    print(json.dumps({
        'configured_hosts_side_collapses_to_one_remote_candidate': configured_hosts_side_collapses_to_one_remote_candidate,
        'artifact_has_alias_multiplicity': artifact_has_alias_multiplicity,
        'source_exposes_both_candidate_axes': source_exposes_both_candidate_axes,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
