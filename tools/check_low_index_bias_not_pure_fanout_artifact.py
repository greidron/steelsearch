import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            'usage: check_low_index_bias_not_pure_fanout_artifact.py '
            '<closeable_channel.java> <finer_first_close.json>',
            file=sys.stderr,
        )
        return 1

    closeable_text = Path(sys.argv[1]).read_text()
    finer = json.loads(Path(sys.argv[2]).read_text())

    source_fanout_closes_in_list_order = 'IOUtils.close(channels);' in closeable_text
    first_index_counts = {int(k): v for k, v in finer['first_index_counts'].items()}
    first_index_zero = first_index_counts.get(0, 0)
    nonzero_first_total = sum(v for i, v in first_index_counts.items() if i != 0)
    distinct_nonzero_first_indices = sorted(i for i, v in first_index_counts.items() if i != 0 and v > 0)

    if source_fanout_closes_in_list_order and nonzero_first_total > 0 and len(distinct_nonzero_first_indices) >= 3:
        result = 'low_index_bias_is_not_explained_by_pure_close_fanout_logging_artifact_because_finer_trace_observes_many_nonzero_first_indices'
    else:
        result = 'low_index_bias_vs_pure_close_fanout_logging_artifact_inconclusive'

    print(json.dumps({
        'source_fanout_closes_in_list_order': source_fanout_closes_in_list_order,
        'connection_count': finer['connection_count'],
        'first_index_zero': first_index_zero,
        'nonzero_first_total': nonzero_first_total,
        'distinct_nonzero_first_indices': distinct_nonzero_first_indices,
        'result': result,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
