#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def normalized_seed_peer_identity(report):
    peer = ((report.get('seed_peer_identity') or {}).get('discovery_node') or {}).copy()
    for key in ('id', 'ephemeral_id', 'transport_address'):
        peer.pop(key, None)
    return peer


def normalized_bootstrap_nodes(report):
    nodes = []
    for node in report.get('steelsearch_bootstrap_remote_nodes') or []:
        node = dict(node)
        node.pop('node_id', None)
        node.pop('transport_address', None)
        nodes.append(node)
    return nodes


def normalized_members(report):
    members = []
    for node in (report.get('steelsearch_membership_members') or []):
        node = dict(node)
        node.pop('node_id', None)
        members.append(node)
    return sorted(members, key=lambda x: x.get('node_name') or '')


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_rust_primary_java_replica_persisted_state_delta.py <formed-report.json> <failed-report.json>', file=sys.stderr)
        return 2

    formed = load(sys.argv[1])
    failed = load(sys.argv[2])

    formed_marker_subset = {k: v for k, v in (formed.get('markers') or {}).items() if k != 'steelsearch_transport_follow_up_observed'}
    failed_marker_subset = {k: v for k, v in (failed.get('markers') or {}).items() if k != 'steelsearch_transport_follow_up_observed'}

    print(f"initial_cluster_manager_nodes_same={formed.get('initial_cluster_manager_nodes') == failed.get('initial_cluster_manager_nodes')}")
    print(f"marker_subset_same={formed_marker_subset == failed_marker_subset}")
    print(f"normalized_seed_peer_identity_same={normalized_seed_peer_identity(formed) == normalized_seed_peer_identity(failed)}")
    print(f"normalized_bootstrap_nodes_same={normalized_bootstrap_nodes(formed) == normalized_bootstrap_nodes(failed)}")
    print(f"normalized_membership_same={normalized_members(formed) == normalized_members(failed)}")
    print(f"formed_follow_up_observed={formed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")
    print(f"failed_follow_up_observed={failed.get('markers', {}).get('steelsearch_transport_follow_up_observed')}")

    if (
        formed.get('membership_formed') is True
        and failed.get('membership_formed') is False
        and formed.get('initial_cluster_manager_nodes') == failed.get('initial_cluster_manager_nodes')
        and formed_marker_subset == failed_marker_subset
        and normalized_seed_peer_identity(formed) == normalized_seed_peer_identity(failed)
        and normalized_bootstrap_nodes(formed) == normalized_bootstrap_nodes(failed)
        and normalized_members(formed) == normalized_members(failed)
        and formed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is True
        and failed.get('markers', {}).get('steelsearch_transport_follow_up_observed') is False
    ):
        print('result=persisted_config_state_same_shape_but_runtime_follow_up_promotion_differs')
        return 0

    print('result=persisted_state_delta_not_yet_decisive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
