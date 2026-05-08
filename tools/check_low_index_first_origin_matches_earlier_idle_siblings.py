import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 5:
        print(
            'usage: check_low_index_first_origin_matches_earlier_idle_siblings.py '
            '<tcp_transport.java> <connection_profile.java> <first_close_vs_action_usage.json> <first_close_classes.json>',
            file=sys.stderr,
        )
        return 1

    tcp_transport_text = Path(sys.argv[1]).read_text()
    connection_profile_text = Path(sys.argv[2]).read_text()
    first_close_vs_action = json.loads(Path(sys.argv[3]).read_text())
    first_close_classes = json.loads(Path(sys.argv[4]).read_text())

    source_opens_channels_in_index_order = re.search(
        r'for \(int i = 0; i < numConnections; \+\+i\) \{.*?channels\.add\(channel\);',
        tcp_transport_text,
        re.S,
    ) is not None
    source_default_profile_starts_bulk_then_ping_state_then_recovery_then_reg = re.search(
        r'addConnections\(connectionsPerNodeBulk,\s*TransportRequestOptions\.Type\.BULK\).*?'
        r'addConnections\(connectionsPerNodePing,\s*TransportRequestOptions\.Type\.PING\).*?'
        r'addConnections\(.*?TransportRequestOptions\.Type\.STATE.*?\).*?'
        r'addConnections\(.*?TransportRequestOptions\.Type\.RECOVERY.*?\).*?'
        r'addConnections\(connectionsPerNodeReg,\s*TransportRequestOptions\.Type\.REG\)',
        connection_profile_text,
        re.S,
    ) is not None

    first_class_counts = first_close_classes['first_class_counts']
    idle_earlier_classes_total = first_class_counts['BULK'] + first_class_counts['RECOVERY']
    active_later_classes_total = first_class_counts['PING'] + first_class_counts['STATE'] + first_class_counts['REG']

    if (
        source_opens_channels_in_index_order
        and source_default_profile_starts_bulk_then_ping_state_then_recovery_then_reg
        and first_close_vs_action['ping_state_actions_present']
        and first_close_vs_action['reg_actions_present']
        and idle_earlier_classes_total > active_later_classes_total
    ):
        result = (
            'actual_first_origin_low_index_bias_is_more_consistent_with_earlier_opened_idle_bulk_recovery_siblings_than_with_active_later_action_channels'
        )
    else:
        result = 'actual_first_origin_low_index_bias_vs_earlier_idle_siblings_inconclusive'

    print(json.dumps({
        'source_opens_channels_in_index_order': source_opens_channels_in_index_order,
        'source_default_profile_starts_bulk_then_ping_state_then_recovery_then_reg': source_default_profile_starts_bulk_then_ping_state_then_recovery_then_reg,
        'action_counts': first_close_vs_action['action_counts'],
        'first_class_counts': first_class_counts,
        'idle_earlier_classes_total': idle_earlier_classes_total,
        'active_later_classes_total': active_later_classes_total,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
