#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"error": "usage: check_registration_boundary_break.py <registration_boundary.json> <mixed_followup.json> <mixed_no_reuse.json>"}))
        return 1

    boundary = load(sys.argv[1])
    followup = load(sys.argv[2])
    noreuse = load(sys.argv[3])

    registration_boundary_present = bool(
        boundary.get('connect_to_node_uses_connection_validator')
        and boundary.get('validator_success_registers_connected_node')
        and boundary.get('registration_triggers_on_node_connected')
        and boundary.get('get_connection_reads_connected_nodes')
        and boundary.get('node_connected_checks_connected_nodes')
    )
    followup_cleared = not bool(followup.get('completed_handshake_followup_failed')) and not bool(followup.get('connection_reset'))
    no_reuse = bool(noreuse.get('all_coordinator_actions_arrive_as_connection_first_frame'))

    if registration_boundary_present and followup_cleared and no_reuse:
        result = 'mixed_runtime_breaks_between_followup_acceptance_and_connected_nodes_registration'
    elif not registration_boundary_present:
        result = 'registration_boundary_not_detected'
    else:
        result = 'boundary_break_not_isolated'

    print(json.dumps({
        'registration_boundary_present': registration_boundary_present,
        'mixed_followup_failure_cleared': followup_cleared,
        'mixed_no_reusable_channel': no_reuse,
        'result': result,
    }))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
