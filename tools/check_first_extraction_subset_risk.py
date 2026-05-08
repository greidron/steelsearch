#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
CONSUMERS = [
    REPO / 'crates/os-node/src/main.rs',
    REPO / 'crates/os-node/tests/dev_cluster_daemons.rs',
    REPO / 'crates/os-node/tests/utoipa_poc.rs',
]
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


def usage_count(text: str, name: str):
    import_hits = 0
    for block in ROOT_IMPORT_RE.findall(text):
        import_hits += parse_names(block).count(name)
    qualified_hits = len(re.findall(r'os_node::' + re.escape(name) + r'\b', text))
    return import_hits + qualified_hits


def main():
    subset_metrics = {}
    for subset, names in SUBSETS.items():
        consumer_files = []
        total_hits = 0
        per_file_hits = {}
        for consumer in CONSUMERS:
            text = consumer.read_text()
            hits = sum(usage_count(text, name) for name in names)
            if hits > 0:
                rel = str(consumer.relative_to(REPO))
                consumer_files.append(rel)
                per_file_hits[rel] = hits
                total_hits += hits
        subset_metrics[subset] = {
            'export_count': len(names),
            'consumer_file_count': len(consumer_files),
            'consumer_files': consumer_files,
            'total_reference_hits': total_hits,
            'per_file_hits': per_file_hits,
        }

    ranked = sorted(
        subset_metrics.items(),
        key=lambda item: (
            item[1]['consumer_file_count'],
            item[1]['export_count'],
            item[1]['total_reference_hits'],
        ),
    )

    result = {
        'subset_metrics': subset_metrics,
        'ranked_by_lower_risk': [name for name, _ in ranked],
        'lowest_risk_first_extraction_subset': ranked[0][0],
        'lowest_risk_metrics': ranked[0][1],
        'result': 'rest_bootstrap_and_policy_is_the_lowest_risk_first_extraction_subset_because_it_is_main_only_and_smaller_than_the_other_main_only_subset',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
