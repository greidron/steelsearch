#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_peerfinder_establish_stops_before_connector_body.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    text = Path(sys.argv[1]).read_text()

    resolved_configured_hosts = text.count("steelsearch_peerfinder_stage=resolved_configured_hosts")
    establish_connection = text.count("steelsearch_peerfinder_stage=establish_connection")
    open_connection_request = text.count("steelsearch_open_connection_stage=request")
    probe_stage = text.count("steelsearch_probe_stage=")
    one_node_election = text.count("elected-as-cluster-manager ([1] nodes joined)")

    print(f"resolved_configured_hosts={resolved_configured_hosts}")
    print(f"establish_connection={establish_connection}")
    print(f"open_connection_request={open_connection_request}")
    print(f"probe_stage={probe_stage}")
    print(f"one_node_election={one_node_election}")

    if establish_connection > 0 and open_connection_request == 0 and probe_stage == 0:
        print("checker_result=peerfinder_establish_stops_before_connector_body_entry")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
