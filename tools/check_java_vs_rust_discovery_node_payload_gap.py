#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_java_vs_rust_discovery_node_payload_gap.py <main.rs> <report.json>"
        )

    main_rs = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    rust_writer_hardcodes_empty_attributes = (
        "write_bool(out, false);" in main_rs and "write_transport_vint_to(out, 0);" in main_rs
    )
    rust_supports_remote_cluster_client_wire_role = (
        '"remote_cluster_client" => ("r", false)' in main_rs
    )

    java_node_id = report["seed_peer_identity"]["discovery_node"]["id"]
    java_roles = report["seed_peer_identity"]["discovery_node"]["roles"]
    rust_member = next(
        member
        for member in report["steelsearch_membership_members"]
        if member["node_id"] != java_node_id
    )
    rust_roles = rust_member["roles"]

    java_has_remote_cluster_client = "remote_cluster_client" in java_roles
    rust_has_remote_cluster_client = "remote_cluster_client" in rust_roles

    result = (
        "rust_local_discovery_node_omits_remote_cluster_client_and_attributes_unlike_java_reference"
        if rust_writer_hardcodes_empty_attributes
        and rust_supports_remote_cluster_client_wire_role
        and java_has_remote_cluster_client
        and not rust_has_remote_cluster_client
        else "no_concrete_discovery_node_payload_gap_detected"
    )

    print(
        json.dumps(
            {
                "rust_writer_hardcodes_empty_attributes": rust_writer_hardcodes_empty_attributes,
                "rust_supports_remote_cluster_client_wire_role": rust_supports_remote_cluster_client_wire_role,
                "java_reference_roles": java_roles,
                "rust_local_roles": rust_roles,
                "java_has_remote_cluster_client": java_has_remote_cluster_client,
                "rust_has_remote_cluster_client": rust_has_remote_cluster_client,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
