#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')


def run_json(script: str):
    out = subprocess.run(
        ['python3', str(REPO / 'tools' / script)],
        cwd=REPO,
        text=True,
        capture_output=True,
        check=True,
    ).stdout
    return json.loads(out)


def main():
    synthetic = run_json('check_helper_lib_split_rebuild_impact.py')
    stronger_need = run_json('check_stronger_crate_split_needed.py')
    lib_text = (REPO / 'crates/os-node/src/lib.rs').read_text()

    has_standalone_runtime_module_boundary = 'pub mod standalone_runtime;' in lib_text
    synthetic_giant_body_move_helps_root_edit = synthetic['root_edit_delta_ms'] >= 100
    current_thin_core_move_did_not_help = stronger_need['fresh_rest_core_after_lib_rs_touch'] and stronger_need['compiling_os_node_after_lib_rs_touch']

    result = {
        'has_standalone_runtime_module_boundary': has_standalone_runtime_module_boundary,
        'standalone_runtime_lines': stronger_need['standalone_runtime_lines'],
        'thin_core_rest_core_lines': stronger_need['rest_core_lines'],
        'synthetic_root_edit_delta_ms': synthetic['root_edit_delta_ms'],
        'synthetic_runtime_edit_delta_ms': synthetic['runtime_edit_delta_ms'],
        'synthetic_giant_body_move_helps_root_edit': synthetic_giant_body_move_helps_root_edit,
        'current_thin_core_move_did_not_help': current_thin_core_move_did_not_help,
        'result': 'the_lowest_risk_stronger_split_candidate_is_moving_the_existing_standalone_runtime_giant_body_behind_a_facade_crate_boundary_not_further_splitting_the_already_small_facade_side',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
