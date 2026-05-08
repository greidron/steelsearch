#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    if len(sys.argv) != 3:
        raise SystemExit('usage: check_next_branch_after_broader_restore_stop.py PREPARE_JSON BROADER_STOP_JSON')
    prepare = load(sys.argv[1])
    stop = load(sys.argv[2])
    result = 'inconclusive'
    if (
        prepare.get('prepare_ready_gate') is False
        and stop.get('checker_result') == 'broader_launch_env_restore_family_reached_practical_stop_without_restoring_followup_or_formed_handoff'
    ):
        result = 'next_productive_branch_is_source_level_restore_candidate_not_more_launch_env_knobs_or_actual_run_backlog'
    print(json.dumps({
        'prepare_ready_gate': prepare.get('prepare_ready_gate'),
        'prepare_ready_node_count': prepare.get('prepare_ready_node_count'),
        'prepare_ready_error': prepare.get('prepare_ready_error'),
        'broader_stop_result': stop.get('checker_result'),
        'checker_result': result,
    }, indent=2))


if __name__ == '__main__':
    main()
