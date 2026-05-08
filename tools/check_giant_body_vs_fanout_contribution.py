#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
SRC = ROOT / 'crates/os-node/src'
STANDALONE = SRC / 'standalone_runtime.rs'
LEAF = SRC / 'write_path_invariants.rs'
BUILD_CMD = [
    'cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime',
    '--bin', 'steelsearch', '--manifest-path', str(ROOT / 'Cargo.toml')
]
BUILD_VV_CMD = [
    'cargo', 'build', '-vv', '-p', 'os-node', '--features', 'standalone-runtime',
    '--bin', 'steelsearch', '--manifest-path', str(ROOT / 'Cargo.toml')
]
RUNNING_RE = re.compile(r'Running `([^`]+)`')
CRATE_RE = re.compile(r'--crate-name\s+([^\s]+)')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_build_ms() -> int:
    t0 = time.time()
    cp = subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def run_build_vv_units(path: Path) -> list[str]:
    touch(path)
    cp = subprocess.run(BUILD_VV_CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    crates = []
    for match in RUNNING_RE.finditer(cp.stdout + '\n' + cp.stderr):
        cmd = match.group(1)
        crate = CRATE_RE.search(cmd)
        if crate:
            crates.append(crate.group(1))
    return crates


def timed_touch_build(path: Path) -> int:
    touch(path)
    return run_build_ms()


def main() -> int:
    baseline_ms = run_build_ms()
    standalone_ms = timed_touch_build(STANDALONE)
    leaf_ms = timed_touch_build(LEAF)
    standalone_units = run_build_vv_units(STANDALONE)
    leaf_units = run_build_vv_units(LEAF)

    result = {
        'baseline_warm_build_ms': baseline_ms,
        'standalone_runtime_ms': standalone_ms,
        'write_path_invariants_ms': leaf_ms,
        'standalone_runtime_units': standalone_units,
        'write_path_invariants_units': leaf_units,
        'same_compile_units': standalone_units == leaf_units,
        'giant_body_additional_cost_ms': standalone_ms - leaf_ms,
        'result': 'standalone_runtime_giant_body_contributes_substantial_extra_cost_beyond_shared_crate_wide_fanout_because_a_tiny_leaf_module_rebuilds_the_same_units_much_faster'
        if standalone_units == leaf_units and standalone_ms > leaf_ms
        else 'shared_fanout_dominates_or_the_measurement_is_inconclusive',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
