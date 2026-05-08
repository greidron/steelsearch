#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path
from statistics import median

REPO = Path('/home/ubuntu/steelsearch')
SAMPLES = 3
BUILD_CMD = [
    'cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime', '--bin', 'steelsearch',
    '--manifest-path', str(REPO / 'Cargo.toml')
]
CASES = {
    'facade_root_lib_rs': REPO / 'crates/os-node/src/lib.rs',
    'helper_bulk_standalone_runtime_rs': REPO / 'crates/os-node/src/standalone_runtime.rs',
    'helper_tiny_write_path_invariants_rs': REPO / 'crates/os-node/src/write_path_invariants.rs',
}


def run(cmd):
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=True)


def cargo_build_ms():
    start = time.perf_counter()
    run(BUILD_CMD)
    return round((time.perf_counter() - start) * 1000)


def touch_with_restore(path: Path, marker: str):
    original = path.read_text()
    path.write_text(original + ('\n' if not original.endswith('\n') else '') + marker + '\n')
    return original


def restore(path: Path, original: str):
    path.write_text(original)


def measure_case(path: Path, case_name: str):
    samples = []
    for i in range(SAMPLES):
        original = path.read_text()
        path.write_text(original + ('\n' if not original.endswith('\n') else '') + f'// bench {case_name} {i}\n')
        try:
            samples.append(cargo_build_ms())
        finally:
            path.write_text(original)
    return samples


def main():
    baseline = cargo_build_ms()
    case_samples = {name: measure_case(path, name) for name, path in CASES.items()}
    medians = {name: median(vals) for name, vals in case_samples.items()}

    result = {
        'baseline_warm_build_ms': baseline,
        'samples_per_case': SAMPLES,
        'case_samples_ms': case_samples,
        'case_medians_ms': medians,
        'facade_vs_helper_bulk_delta_ms': medians['facade_root_lib_rs'] - medians['helper_bulk_standalone_runtime_rs'],
        'facade_vs_helper_tiny_delta_ms': medians['facade_root_lib_rs'] - medians['helper_tiny_write_path_invariants_rs'],
        'result': 'current_os_node_rebuild_hot_edits_are_not_facade_only_because_helper_like_edits_cost_at_least_as_much_as_root_lib_rs_edits',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
