#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_cluster_state_vs_configured_hosts_candidates.py <PeerFinder.java> <probe_java_rust_mixed_membership.sh>')

    source = Path(sys.argv[1]).read_text()
    probe = Path(sys.argv[2]).read_text()

    source_has_cluster_state_cluster_manager_probe_source = (
        'for (final DiscoveryNode discoveryNodeObjectCursor : lastAcceptedNodes.getClusterManagerNodes().values()) {' in source
        and 'startProbe(discoveryNodeObjectCursor.getAddress());' in source
    )
    source_has_configured_hosts_probe_source = (
        'configuredHostsResolver.resolveConfiguredHosts' in source
        and 'providedAddresses.forEach(this::startProbe);' in source
    )

    runtime_sets_dual_seed_hosts = 'SEEDS="127.0.0.1:${OS_TRANSPORT},127.0.0.1:${SS_TRANSPORT}"' in probe
    runtime_validated_mode_expands_initial_cluster_manager_nodes_to_java_and_rust = (
        'elif [[ -n "${JAVA_RUST_MIXED_MEMBERSHIP_JAVA_WRITE_FORWARDING_VALIDATED:-}" ]]; then' in probe
        and 'INITIAL_CLUSTER_MANAGER_NODES="${JAVA_NODE_NAME},${RUST_NODE_NAME}"' in probe
    )

    result = (
        'current_mixed_probe_runtime_exposes_both_cluster_state_cluster_manager_nodes_and_configured_hosts_as_remaining_alias_entry_sources'
        if source_has_cluster_state_cluster_manager_probe_source
        and source_has_configured_hosts_probe_source
        and runtime_sets_dual_seed_hosts
        and runtime_validated_mode_expands_initial_cluster_manager_nodes_to_java_and_rust
        else 'cluster_state_vs_configured_hosts_candidates_not_fully_established'
    )

    print(json.dumps({
        'source_has_cluster_state_cluster_manager_probe_source': source_has_cluster_state_cluster_manager_probe_source,
        'source_has_configured_hosts_probe_source': source_has_configured_hosts_probe_source,
        'runtime_sets_dual_seed_hosts': runtime_sets_dual_seed_hosts,
        'runtime_validated_mode_expands_initial_cluster_manager_nodes_to_java_and_rust': runtime_validated_mode_expands_initial_cluster_manager_nodes_to_java_and_rust,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
