#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            'usage: check_restart_loop_reenters_connector_probe.py <followup_contract.json> <next_action_pattern.json>'
        )

    contract = load(sys.argv[1])
    pattern = load(sys.argv[2])

    source_connector_probe_contract = (
        contract.get('probe_connection_uses_single_reg_channel_profile') is True
        and contract.get('handshake_success_closes_probe_connection_before_full_connect') is True
        and contract.get('full_connection_happens_via_transport_service_connect_to_node') is True
    )
    restarts_to_tcp_handshake = (
        pattern.get('restart_observation_count', 0) > 0
        and pattern.get('next_action_counts') == {'internal:tcp/handshake': pattern.get('restart_observation_count')}
    )

    result = (
        'restart_loop_reenters_handshaking_transport_address_connector_probe_entrypoint'
        if source_connector_probe_contract and restarts_to_tcp_handshake
        else 'restart_loop_probe_reentry_not_fully_established'
    )

    print(json.dumps({
        'source_connector_probe_contract': source_connector_probe_contract,
        'restart_observation_count': pattern.get('restart_observation_count'),
        'restarts_to_tcp_handshake': restarts_to_tcp_handshake,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
