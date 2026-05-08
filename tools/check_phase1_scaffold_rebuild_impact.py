#!/usr/bin/env python3
import json
import re
import subprocess
import time
from pathlib import Path
from statistics import median

REPO = Path('/home/ubuntu/steelsearch')
TASKS = REPO / 'tasks.md'
SAMPLES = 3
BUILD_CMD = [
    'cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime', '--bin', 'steelsearch',
    '--manifest-path', str(REPO / 'Cargo.toml')
]
OS_NODE_LIB = REPO / 'crates/os-node/src/lib.rs'
REST_CORE_LIB = REPO / 'crates/os-node-rest-core/src/lib.rs'


def run(cmd):
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=True)


def cargo_build_ms():
    start = time.perf_counter()
    run(BUILD_CMD)
    return round((time.perf_counter() - start) * 1000)


def measure(path: Path, label: str):
    samples = []
    for i in range(SAMPLES):
        original = path.read_text()
        path.write_text(original + ('\n' if not original.endswith('\n') else '') + f'// phase1 bench {label} {i}\n')
        try:
            samples.append(cargo_build_ms())
        finally:
            path.write_text(original)
    return samples


def parse_previous_median_ms() -> int:
    text = TASKS.read_text()
    m = re.search(r'`lib\.rs` median `([0-9]+)ms`', text)
    if not m:
        raise RuntimeError('previous lib.rs median not found in tasks.md')
    return int(m.group(1))


def main():
    previous_lib_median = parse_previous_median_ms()
    baseline = cargo_build_ms()
    current_lib_samples = measure(OS_NODE_LIB, 'os_node_lib_rs')
    helper_core_samples = measure(REST_CORE_LIB, 'os_node_rest_core_lib_rs')
    current_lib_median = median(current_lib_samples)
    helper_core_median = median(helper_core_samples)

    result = {
        'previous_pre_scaffold_os_node_lib_median_ms': previous_lib_median,
        'current_baseline_warm_build_ms': baseline,
        'current_os_node_lib_samples_ms': current_lib_samples,
        'current_os_node_lib_median_ms': current_lib_median,
        'current_rest_core_lib_samples_ms': helper_core_samples,
        'current_rest_core_lib_median_ms': helper_core_median,
        'os_node_lib_delta_vs_pre_scaffold_ms': current_lib_median - previous_lib_median,
        'rest_core_vs_current_os_node_lib_delta_ms': helper_core_median - current_lib_median,
        'result': 'phase1_real_scaffold_has_little_to_no_positive_effect_on_os_node_root_edit_rebuild_cost_if_the_root_edit_still_rebuilds_the_large_os_node_lib_crate',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
