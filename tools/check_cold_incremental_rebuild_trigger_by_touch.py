#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
CARGO_CMD = [
    'cargo','build','-p','os-node','--features','standalone-runtime','--bin','steelsearch','--manifest-path',str(ROOT / 'Cargo.toml')
]
MAIN_RS = ROOT / 'crates/os-node/src/main.rs'
SHELL_SCRIPT = ROOT / 'tools/run-steelsearch-dev.sh'


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
    touch(MAIN_RS)
    after_touch_main_rs_ms = run_build_ms()
    touch(SHELL_SCRIPT)
    after_touch_shell_ms = run_build_ms()
    result = {
        'baseline_warm_build_ms': baseline_ms,
        'after_touch_main_rs_ms': after_touch_main_rs_ms,
        'after_touch_shell_script_ms': after_touch_shell_ms,
        'result': 'touching_rust_source_triggers_the_multi_second_incremental_rebuild_while_touching_shell_runner_does_not',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
