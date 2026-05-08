#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
LIB_RS = REPO / 'crates/os-node/src/lib.rs'
CONSUMERS = [
    REPO / 'crates/os-node/src/main.rs',
    REPO / 'crates/os-node/tests/dev_cluster_daemons.rs',
    REPO / 'crates/os-node/tests/utoipa_poc.rs',
]
REEXPORT_RE = re.compile(r'pub use standalone_runtime::\{(.*?)\};', re.S)
ROOT_IMPORT_RE = re.compile(r'use\s+os_node::\{(.*?)\};', re.S)

SUBSETS = {
    'cluster_manager_tasking': [
        'ClusterManagerTask',
        'ClusterManagerTaskKind',
        'ClusterManagerTaskRecord',
        'ClusterManagerTaskState',
        'CoordinationFaultPhase',
        'PersistedClusterManagerTaskQueueState',
    ],
    'coordination_and_membership_runtime': [
        'ClusterCoordinationState',
        'DevelopmentClusterNode',
        'DevelopmentClusterView',
        'DevelopmentCoordinationStatus',
        'DevelopmentDiscoveryRuntime',
        'DiscoveryConfig',
        'DiscoveryPeer',
        'ElectionAttemptWindow',
        'ElectionResult',
        'ElectionScheduler',
        'ElectionSchedulerConfig',
        'ExtensionBoundaryRegistry',
        'LiveTransportDiscoveryPeerProber',
        'MembershipNode',
        'ProductionMembershipState',
    ],
    'gateway_and_publication_state': [
        'ClusterSettingsState',
        'PersistedGatewayMetadataCommitState',
        'PersistedGatewayMetadataState',
        'PersistedGatewayRoutingMetadata',
        'PersistedGatewayState',
        'PersistedPublicationState',
        'PublicationRoundState',
        'apply_gateway_metadata_commit_state_to_manifest',
        'apply_gateway_metadata_state_to_manifest',
        'collect_live_publication_acknowledgement_details',
        'collect_live_publication_apply_details',
        'load_gateway_state_manifest',
        'persist_gateway_state_manifest',
    ],
    'rest_bootstrap_and_policy': [
        'ReleaseReadinessChecklist',
        'RestServerConfig',
        'SecurityBoundaryPolicy',
        'SteelNode',
        'bind_rest_http_listener',
        'serve_rest_http_listener_until',
        'validate_production_mode_request',
    ],
}


def parse_names(block: str):
    out = []
    for part in block.replace('\n', ' ').split(','):
        name = part.strip()
        if name:
            out.append(name)
    return out


def find_usage(path: Path, name: str):
    text = path.read_text()
    import_hit = False
    for block in ROOT_IMPORT_RE.findall(text):
        if name in parse_names(block):
            import_hit = True
            break
    qualified_hits = len(re.findall(r'os_node::' + re.escape(name) + r'\b', text))
    return import_hit or qualified_hits > 0


def main():
    lib_text = LIB_RS.read_text()
    m = REEXPORT_RE.search(lib_text)
    if not m:
        raise RuntimeError('reexport block not found')
    exported = sorted(parse_names(m.group(1)))
    subset_names = sorted(name for names in SUBSETS.values() for name in names)

    missing_from_partition = sorted(set(exported) - set(subset_names))
    extra_in_partition = sorted(set(subset_names) - set(exported))
    duplicate_count = len(subset_names) - len(set(subset_names))

    consumer_usage = {}
    for subset, names in SUBSETS.items():
        users = []
        for consumer in CONSUMERS:
            rel = str(consumer.relative_to(REPO))
            if any(find_usage(consumer, name) for name in names):
                users.append(rel)
        consumer_usage[subset] = users

    result = {
        'subset_counts': {k: len(v) for k, v in SUBSETS.items()},
        'total_partitioned_exports': sum(len(v) for v in SUBSETS.values()),
        'exported_reexport_count': len(exported),
        'missing_from_partition': missing_from_partition,
        'extra_in_partition': extra_in_partition,
        'duplicate_count': duplicate_count,
        'consumer_usage_by_subset': consumer_usage,
        'subsets': SUBSETS,
        'result': 'the_41_active_exports_can_be_partitioned_into_four_coherent_helper_lib_candidate_subsets_covering_tasking_coordination_gateway_publication_and_rest_bootstrap_policy',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
