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
    split_bench = run_json('check_helper_lib_split_rebuild_impact.py')
    current_hot = run_json('check_current_repo_hot_edit_class.py')
    facade_surface = run_json('check_facade_only_edit_class_size_and_importance.py')

    performance_case_is_narrow = split_bench['root_edit_delta_ms'] > 0 and split_bench['runtime_edit_delta_ms'] <= 0
    current_hot_edits_are_helper_like = (
        current_hot['case_medians_ms']['helper_bulk_standalone_runtime_rs'] >= current_hot['case_medians_ms']['facade_root_lib_rs']
        and current_hot['case_medians_ms']['helper_tiny_write_path_invariants_rs'] >= current_hot['case_medians_ms']['facade_root_lib_rs']
    )
    facade_surface_is_small = facade_surface['facade_line_share'] < 0.01
    facade_surface_is_real_api = facade_surface['unique_root_import_count'] >= 10 and facade_surface['matched_reexport_count'] >= 10

    if performance_case_is_narrow and current_hot_edits_are_helper_like:
        performance_classification = 'weak_for_current_hotspot'
    else:
        performance_classification = 'plausible_for_current_hotspot'

    if facade_surface_is_small and facade_surface_is_real_api:
        governance_classification = 'strong_root_api_surface_candidate'
    else:
        governance_classification = 'weak_root_api_surface_candidate'

    result = {
        'split_bench_root_edit_delta_ms': split_bench['root_edit_delta_ms'],
        'split_bench_runtime_edit_delta_ms': split_bench['runtime_edit_delta_ms'],
        'current_repo_facade_root_median_ms': current_hot['case_medians_ms']['facade_root_lib_rs'],
        'current_repo_helper_bulk_median_ms': current_hot['case_medians_ms']['helper_bulk_standalone_runtime_rs'],
        'current_repo_helper_tiny_median_ms': current_hot['case_medians_ms']['helper_tiny_write_path_invariants_rs'],
        'facade_line_share': facade_surface['facade_line_share'],
        'unique_root_import_count': facade_surface['unique_root_import_count'],
        'matched_reexport_count': facade_surface['matched_reexport_count'],
        'performance_case_is_narrow': performance_case_is_narrow,
        'current_hot_edits_are_helper_like': current_hot_edits_are_helper_like,
        'facade_surface_is_small': facade_surface_is_small,
        'facade_surface_is_real_api': facade_surface_is_real_api,
        'performance_refactor_classification': performance_classification,
        'governance_refactor_classification': governance_classification,
        'result': 'helper_lib_split_is_better_classified_as_a_root_api_surface_governance_refactor_than_as_a_primary_current_hotspot_performance_refactor',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
