#!/usr/bin/env python3
import json
import os
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
CARGO_CMD = [
    'cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime',
    '--bin', 'steelsearch', '--manifest-path', str(ROOT / 'Cargo.toml')
]
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
STANDALONE_RUNTIME_RS = ROOT / 'crates/os-node/src/standalone_runtime.rs'
ROUNDS = 4


def run_build_ms() -> int:
    t0 = time.time()
    cp = subprocess.run(CARGO_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def sample_costs(path: Path, rounds: int) -> list[int]:
    samples = []
    for _ in range(rounds):
        touch(path)
        samples.append(run_build_ms())
    return samples


def summarize(samples: list[int]) -> dict:
    return {
        'min_ms': min(samples),
        'max_ms': max(samples),
        'median_ms': int(statistics.median(samples)),
        'samples_ms': samples,
    }


def main() -> int:
    warm_baseline_ms = run_build_ms()
    lib_samples = sample_costs(LIB_RS, ROUNDS)
    standalone_samples = sample_costs(STANDALONE_RUNTIME_RS, ROUNDS)

    lib_summary = summarize(lib_samples)
    standalone_summary = summarize(standalone_samples)
    median_diff_ms = lib_summary['median_ms'] - standalone_summary['median_ms']
    sign_flips_against_previous_claim = median_diff_ms <= 0
    ranges_overlap = not (
        lib_summary['min_ms'] > standalone_summary['max_ms']
        or standalone_summary['min_ms'] > lib_summary['max_ms']
    )

    result = {
        'warm_baseline_ms': warm_baseline_ms,
        'lib_rs': lib_summary,
        'standalone_runtime_rs': standalone_summary,
        'median_diff_ms': median_diff_ms,
        'sign_flips_against_previous_claim': sign_flips_against_previous_claim,
        'ranges_overlap': ranges_overlap,
        'result': 'lib_rs_vs_standalone_runtime_rs_extra_cost_is_not_stable_enough_to_support_a_strong_reexport_metadata_invalidation_claim'
        if sign_flips_against_previous_claim or ranges_overlap
        else 'lib_rs_shows_a_stable_extra_cost_over_standalone_runtime_rs',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
