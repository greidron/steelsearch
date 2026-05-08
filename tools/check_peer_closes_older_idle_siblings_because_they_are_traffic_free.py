import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_peer_closes_older_idle_siblings_because_they_are_traffic_free.py '
            '<bulk_recovery_vs_workload.json> <first_close_vs_action_usage.json> <report.json>',
            file=sys.stderr,
        )
        return 1

    bulk_recovery_vs_workload = json.loads(Path(sys.argv[1]).read_text())
    first_close_vs_action = json.loads(Path(sys.argv[2]).read_text())
    report_text = Path(sys.argv[3]).read_text()

    start_join_present = 'internal:cluster/coordination/start_join' in report_text
    pre_vote_present = 'internal:cluster/request_pre_vote' in report_text
    transport_handshake_present = 'internal:transport/handshake' in report_text
    tcp_handshake_present = 'internal:tcp/handshake' in report_text

    no_bulk_or_recovery_actions = bulk_recovery_vs_workload['bulk_or_recovery_action_hints'] == {}
    later_control_traffic_present = (
        first_close_vs_action['action_counts']['request_peers'] > 0
        and first_close_vs_action['action_counts']['follower_check'] > 0
        and first_close_vs_action['action_counts']['publish_state'] > 0
        and start_join_present
        and pre_vote_present
        and transport_handshake_present
        and tcp_handshake_present
    )
    bulk_recovery_first_close_dominant = (
        bulk_recovery_vs_workload['bulk_recovery_first_close_total']
        > bulk_recovery_vs_workload['ping_state_reg_first_close_total']
    )

    if no_bulk_or_recovery_actions and later_control_traffic_present and bulk_recovery_first_close_dominant:
        result = (
            'peer_side_first_close_prefers_older_bulk_recovery_siblings_because_current_artifact_shows_them_as_the_traffic_free_channels_while_later_channels_carry_control_traffic'
        )
    else:
        result = 'peer_side_first_close_preference_for_older_idle_siblings_inconclusive'

    print(json.dumps({
        'no_bulk_or_recovery_actions': no_bulk_or_recovery_actions,
        'later_control_traffic_present': later_control_traffic_present,
        'start_join_present': start_join_present,
        'pre_vote_present': pre_vote_present,
        'transport_handshake_present': transport_handshake_present,
        'tcp_handshake_present': tcp_handshake_present,
        'action_counts': first_close_vs_action['action_counts'],
        'first_class_counts': first_close_vs_action['first_class_counts'],
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
