#!/usr/bin/env python3
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
CARGO_CMD = [
    'cargo','build','-p','os-node','--features','standalone-runtime','--bin','steelsearch','--manifest-path',str(ROOT / 'Cargo.toml')
]
FILES = [
    ROOT / 'crates/os-node/src/main.rs',
    ROOT / 'crates/os-node/src/lib.rs',
    ROOT / 'crates/os-node/src/standalone_runtime.rs',
]


def run_build_ms() -> int:
    t0 = time.time()
    cp = subprocess.run(CARGO_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    baseline_ms = run_build_ms()
    costs = {}
    for path in FILES:
        touch(path)
        costs[path.name] = run_build_ms()
    max_file = max(costs, key=costs.get)
    result = {
        'baseline_warm_build_ms': baseline_ms,
        'file_rebuild_cost_ms': costs,
        'max_cost_file': max_file,
        'max_cost_ms': costs[max_file],
        'result': 'os_node_internal_rebuild_costs_measured_by_touching_minimal_source_file_set',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
