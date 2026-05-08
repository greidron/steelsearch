#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_validator_mismatch_after_equivalent_identity.py <TransportService.java> <identity_equivalence.json>"
        )

    transport_service = Path(sys.argv[1]).read_text()
    equivalence = json.loads(Path(sys.argv[2]).read_text())

    source_validator_checks_node_equals_remote = (
        "if (node.equals(remote) == false)" in transport_service
        and 'throw new ConnectTransportException(node, "handshake failed. unexpected remote node " + remote);' in transport_service
    )
    identity_equivalent = equivalence.get("responses_equivalent") is True

    result = (
        "validator_mismatch_is_not_supported_by_artifact_once_probe_and_direct_transport_handshake_identities_are_equivalent"
        if source_validator_checks_node_equals_remote and identity_equivalent
        else "validator_mismatch_gap_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "source_validator_checks_node_equals_remote": source_validator_checks_node_equals_remote,
                "identity_equivalent": identity_equivalent,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
