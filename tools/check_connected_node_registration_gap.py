#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"error": "usage: check_connected_node_registration_gap.py <followup_contract.json> <mixed_followup_check.json> <mixed_no_reuse_check.json>"}))
        return 1

    contract = load(sys.argv[1])
    followup = load(sys.argv[2])
    noreuse = load(sys.argv[3])

    source_full_connect_contract = bool(
        contract.get('probe_connection_uses_single_reg_channel_profile')
        and contract.get('handshake_success_closes_probe_connection_before_full_connect')
        and contract.get('full_connection_happens_via_transport_service_connect_to_node')
    )
    followup_failure_cleared = not bool(followup.get('completed_handshake_followup_failed')) and not bool(
        followup.get('connection_reset')
    )
    no_reusable_channel = bool(
        noreuse.get('all_coordinator_actions_arrive_as_connection_first_frame')
        and noreuse.get('result') == 'mixed_runtime_never_establishes_reusable_node_channel_so_publication_stays_on_one_shot_sockets'
    )

    if source_full_connect_contract and followup_failure_cleared and no_reusable_channel:
        result = 'followup_failure_cleared_but_full_connection_promotion_or_registration_still_missing_in_mixed_runtime'
    elif not source_full_connect_contract:
        result = 'source_full_connect_contract_not_detected'
    else:
        result = 'registration_gap_not_isolated'

    print(json.dumps({
        'source_full_connect_contract': source_full_connect_contract,
        'mixed_followup_failure_cleared': followup_failure_cleared,
        'mixed_no_reusable_channel': no_reusable_channel,
        'result': result,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
