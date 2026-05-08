import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_first_close_bias_matches_idle_classes.py '
            '<connection_profile.java> <first_close_vs_action_usage.json> <bulk_recovery_vs_workload.json>',
            file=sys.stderr,
        )
        return 1

    connection_profile_text = Path(sys.argv[1]).read_text()
    first_close_vs_action = json.loads(Path(sys.argv[2]).read_text())
    bulk_recovery_vs_workload = json.loads(Path(sys.argv[3]).read_text())

    source_has_default_class_order = all(token in connection_profile_text for token in [
        'TransportRequestOptions.Type.BULK',
        'TransportRequestOptions.Type.PING',
        'TransportRequestOptions.Type.STATE',
        'TransportRequestOptions.Type.RECOVERY',
        'TransportRequestOptions.Type.REG',
    ])

    first_class_counts = first_close_vs_action['first_class_counts']
    active_action_classes = {
        'REG': first_class_counts['REG'],
        'PING': first_class_counts['PING'],
        'STATE': first_class_counts['STATE'],
    }
    idle_classes = {
        'BULK': first_class_counts['BULK'],
        'RECOVERY': first_class_counts['RECOVERY'],
    }

    idle_first_close_total = sum(idle_classes.values())
    active_first_close_total = sum(active_action_classes.values())

    if (
        source_has_default_class_order
        and first_close_vs_action['ping_state_actions_present']
        and first_close_vs_action['reg_actions_present']
        and bulk_recovery_vs_workload['bulk_or_recovery_action_hints'] == {}
        and idle_first_close_total > active_first_close_total
    ):
        result = (
            'first_close_bias_is_best_explained_by_idle_bulk_recovery_sibling_channels_not_by_active_reg_ping_state_action_channels'
        )
    else:
        result = 'first_close_idle_vs_active_class_bias_inconclusive'

    print(json.dumps({
        'source_has_default_class_order': source_has_default_class_order,
        'action_counts': first_close_vs_action['action_counts'],
        'bulk_or_recovery_action_hints': bulk_recovery_vs_workload['bulk_or_recovery_action_hints'],
        'idle_classes': idle_classes,
        'active_action_classes': active_action_classes,
        'idle_first_close_total': idle_first_close_total,
        'active_first_close_total': active_first_close_total,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
