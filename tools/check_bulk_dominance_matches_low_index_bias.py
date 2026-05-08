import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            'usage: check_bulk_dominance_matches_low_index_bias.py '
            '<closeable_channel.java> <connection_profile.java> <first_close_classes.json>',
            file=sys.stderr,
        )
        return 1

    closeable_text = Path(sys.argv[1]).read_text()
    connection_profile_text = Path(sys.argv[2]).read_text()
    first_close = json.loads(Path(sys.argv[3]).read_text())

    source_close_channels_iterates_list_order = 'IOUtils.close(channels);' in closeable_text
    source_default_profile_starts_with_bulk = re.search(
        r'addConnections\(connectionsPerNodeBulk,\s*TransportRequestOptions\.Type\.BULK\).*?'
        r'addConnections\(connectionsPerNodePing,\s*TransportRequestOptions\.Type\.PING\)',
        connection_profile_text,
        re.S,
    ) is not None

    first_index_counts = {int(k): v for k, v in first_close['first_index_counts'].items()}
    bulk_indices_total = sum(first_index_counts.get(i, 0) for i in (0, 1, 2))
    recovery_indices_total = sum(first_index_counts.get(i, 0) for i in (5, 6))
    later_reg_indices_total = sum(first_index_counts.get(i, 0) for i in (7, 8, 9, 10, 11, 12))
    low_indices_total = sum(first_index_counts.get(i, 0) for i in range(0, 3))
    non_low_indices_total = sum(v for i, v in first_index_counts.items() if i >= 3)

    if (
        source_close_channels_iterates_list_order
        and source_default_profile_starts_with_bulk
        and bulk_indices_total > recovery_indices_total
        and bulk_indices_total > later_reg_indices_total
        and low_indices_total > non_low_indices_total
    ):
        result = 'bulk_dominance_is_more_consistent_with_low_index_bias_than_with_bulk_specific_workload_semantics'
    else:
        result = 'bulk_dominance_vs_low_index_bias_inconclusive'

    print(json.dumps({
        'source_close_channels_iterates_list_order': source_close_channels_iterates_list_order,
        'source_default_profile_starts_with_bulk': source_default_profile_starts_with_bulk,
        'first_index_counts': first_index_counts,
        'bulk_indices_total': bulk_indices_total,
        'recovery_indices_total': recovery_indices_total,
        'later_reg_indices_total': later_reg_indices_total,
        'low_indices_total': low_indices_total,
        'non_low_indices_total': non_low_indices_total,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
