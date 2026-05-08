import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_bulk_recovery_first_close_not_due_to_workload.py '
            '<connection_profile.java> <first_close_classes.json> <report.json>',
            file=sys.stderr,
        )
        return 1

    connection_profile_text = Path(sys.argv[1]).read_text()
    first_close = json.loads(Path(sys.argv[2]).read_text())
    report_text = Path(sys.argv[3]).read_text()

    source_default_profile_orders_bulk_before_ping_state_recovery_reg = re.search(
        r'addConnections\(connectionsPerNodeBulk,\s*TransportRequestOptions\.Type\.BULK\).*?'
        r'addConnections\(connectionsPerNodePing,\s*TransportRequestOptions\.Type\.PING\).*?'
        r'addConnections\(.*?TransportRequestOptions\.Type\.STATE.*?\).*?'
        r'addConnections\(.*?TransportRequestOptions\.Type\.RECOVERY.*?\).*?'
        r'addConnections\(connectionsPerNodeReg,\s*TransportRequestOptions\.Type\.REG\)',
        connection_profile_text,
        re.S,
    ) is not None

    action_hints = re.findall(r'"action_hint"\s*:\s*"([^"]+)"', report_text)
    action_hint_counts = {}
    for action_hint in action_hints:
        action_hint_counts[action_hint] = action_hint_counts.get(action_hint, 0) + 1

    bulk_or_recovery_action_hints = {
        k: v
        for k, v in action_hint_counts.items()
        if 'bulk' in k or 'recovery' in k
    }

    first_class_counts = first_close['first_class_counts']
    bulk_recovery_first_close_total = first_class_counts['BULK'] + first_class_counts['RECOVERY']
    ping_state_reg_first_close_total = (
        first_class_counts['PING'] + first_class_counts['STATE'] + first_class_counts['REG']
    )

    if (
        source_default_profile_orders_bulk_before_ping_state_recovery_reg
        and len(bulk_or_recovery_action_hints) == 0
        and bulk_recovery_first_close_total > ping_state_reg_first_close_total
    ):
        result = (
            'bulk_recovery_first_close_skew_is_better_explained_by_idle_default_channel_ordering_artifact_than_by_actual_bulk_or_recovery_workload'
        )
    else:
        result = 'bulk_recovery_first_close_skew_vs_workload_inconclusive'

    print(json.dumps({
        'source_default_profile_orders_bulk_before_ping_state_recovery_reg': source_default_profile_orders_bulk_before_ping_state_recovery_reg,
        'action_hint_counts': action_hint_counts,
        'bulk_or_recovery_action_hints': bulk_or_recovery_action_hints,
        'first_class_counts': first_close['first_class_counts'],
        'bulk_recovery_first_close_total': bulk_recovery_first_close_total,
        'ping_state_reg_first_close_total': ping_state_reg_first_close_total,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
