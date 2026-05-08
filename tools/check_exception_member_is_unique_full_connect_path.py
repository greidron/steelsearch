#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_exception_member_is_unique_full_connect_path.py <followup_contract.json> <round_role.json>')

    contract = load(sys.argv[1])
    role = load(sys.argv[2])

    source_has_full_connect_after_probe = (
        contract.get('probe_connection_uses_single_reg_channel_profile') is True
        and contract.get('handshake_success_closes_probe_connection_before_full_connect') is True
        and contract.get('full_connection_happens_via_transport_service_connect_to_node') is True
    )
    artifact_has_unique_direct_full_connect_member = (
        role.get('same_round_direct_full_connect_count') == 1
        and role.get('same_round_request_peers_count', 0) >= 3
        and role.get('same_round_tcp_count', 0) >= 1
    )

    result = (
        'exception_socket_is_unique_full_connect_promotion_member_inside_peerfinder_round'
        if source_has_full_connect_after_probe and artifact_has_unique_direct_full_connect_member
        else 'exception_full_connect_promotion_member_not_fully_established'
    )

    print(json.dumps({
        'source_has_full_connect_after_probe': source_has_full_connect_after_probe,
        'artifact_has_unique_direct_full_connect_member': artifact_has_unique_direct_full_connect_member,
        'result': result,
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
