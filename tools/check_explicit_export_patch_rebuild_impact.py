#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
LEAF = ROOT / 'crates/os-node/src/write_path_invariants.rs'
BUILD_CMD = [
    'cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime',
    '--bin', 'steelsearch', '--manifest-path', str(ROOT / 'Cargo.toml')
]
ROUNDS = 3


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_build_ms() -> int:
    t0 = time.time()
    cp = subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def benchmark_mode(lib_text: str) -> list[int]:
    LIB_RS.write_text(lib_text)
    run_build_ms()
    samples = []
    for _ in range(ROUNDS):
        touch(LEAF)
        samples.append(run_build_ms())
    return samples


def median(values: list[int]) -> int:
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def main() -> int:
    original = LIB_RS.read_text()
    star = re.sub(
        r'pub use standalone_runtime::\{.*?\n\};',
        'pub use standalone_runtime::*;',
        original,
        flags=re.S,
    )
    if star == original:
        raise SystemExit('explicit export block not found')

    try:
        star_samples = benchmark_mode(star)
        explicit_samples = benchmark_mode(original)
    finally:
        LIB_RS.write_text(original)

    result = {
        'star_samples_ms': star_samples,
        'explicit_samples_ms': explicit_samples,
        'star_median_ms': median(star_samples),
        'explicit_median_ms': median(explicit_samples),
        'median_delta_ms': median(explicit_samples) - median(star_samples),
        'result': 'explicit_export_patch_rebuild_impact_benchmarked_against_star_reexport',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
