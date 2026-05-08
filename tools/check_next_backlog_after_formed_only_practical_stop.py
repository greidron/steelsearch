#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def parse_prepare(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def parse_stop(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_next_backlog_after_formed_only_practical_stop.py PREPARE_PHASE_JSON FORMED_STOP_CHECKER_JSON')
    prepare = parse_prepare(sys.argv[1])
    stop = parse_stop(sys.argv[2])
    stop_result = stop.get('checker_result')
    result = 'inconclusive'
    if (
        prepare.get('prepare_ready_gate') is False
        and stop_result == 'fresh_formed_only_regression_remaining_unknown_matches_existing_full_opensearch_read_starvation_practical_stop'
    ):
        result = 'next_productive_branch_is_stronger_formed_producer_restore_candidate_not_bulk_replay_actual_run'
    print(json.dumps({
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'prepare_ready_error': prepare.get('prepare_ready_error'),
        'formed_only_stop_checker_result': stop_result,
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
