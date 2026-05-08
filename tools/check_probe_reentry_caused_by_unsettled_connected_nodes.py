#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_probe_reentry_caused_by_unsettled_connected_nodes.py <registration_boundary.json> <probe_reentry.json>'
        )

    registration = load(sys.argv[1])
    probe = load(sys.argv[2])

    source_close_listener_unregisters = (
        registration.get('validator_success_registers_connected_node') is True
        and registration.get('node_connected_checks_connected_nodes') is True
        and registration.get('close_listener_unregisters_connected_node') is True
    )
    dominant_path_reenters_probe = (
        probe.get('source_connector_probe_contract') is True
        and probe.get('restarts_to_tcp_handshake') is True
        and probe.get('restart_observation_count', 0) > 0
    )

    result = (
        'dominant_restart_path_reenters_probe_because_connection_close_prevents_settled_connected_nodes_reuse'
        if source_close_listener_unregisters and dominant_path_reenters_probe
        else 'probe_reentry_unsettled_connected_nodes_cause_not_fully_established'
    )

    print(json.dumps({
        'source_close_listener_unregisters': source_close_listener_unregisters,
        'dominant_path_reenters_probe': dominant_path_reenters_probe,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
