#!/usr/bin/env python3
import sys
from pathlib import Path

if len(sys.argv) != 4:
    print(
        "usage: check_join_source_identity_points_away_from_basic_mismatch.py <main.rs> <Publication.java> <DiscoveryNode.java>",
        file=sys.stderr,
    )
    sys.exit(2)

main_rs = Path(sys.argv[1]).read_text()
publication = Path(sys.argv[2]).read_text()
discovery = Path(sys.argv[3]).read_text()

checks = {
    "handshake_identity_uses_transport_ephemeral_id": 'write_string(&mut payload, &transport_identity.ephemeral_id);' in main_rs,
    "publish_join_uses_same_transport_ephemeral_id": '            &transport_identity.ephemeral_id,' in main_rs,
    "helper_passes_same_local_ephemeral_id": '.arg("--local-ephemeral-id")' in main_rs and '.arg(&transport_identity.ephemeral_id)' in main_rs,
    "rust_transport_identity_is_synthetic_but_stable_per_process": 'ephemeral_id: format!("{}-ephemeral", config.node_id),' in main_rs,
    "rust_default_roles_include_cluster_manager": '"cluster_manager".to_string(),' in main_rs,
    "publication_asserts_join_source_matches_discovery_node": 'assert discoveryNode.equals(join.getSourceNode());' in publication,
    "discovery_node_equals_is_ephemeral_id_based": 'return ephemeralId.equals(that.ephemeralId);' in discovery,
}

for key, value in checks.items():
    print(f"{key}={str(value).lower()}")

if not all(checks.values()):
    print('result=missing_required_source_evidence')
    sys.exit(1)

print('result=join_source_basic_identity_reuses_the_same_transport_identity_so_remaining_risk_points_beyond_basic_source_node_identity_mismatch')
