#!/usr/bin/env python3
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
COMMON = ['cargo','build','-p','os-node','--features','standalone-runtime','--manifest-path',str(ROOT / 'Cargo.toml')]
LIB_CMD = COMMON + ['--lib']
BIN_CMD = COMMON + ['--bin','steelsearch']


def run_ms(cmd):
    t0 = time.time()
    cp = subprocess.run(cmd, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return int((time.time() - t0) * 1000)


def touch(path: Path):
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    baseline_bin_ms = run_ms(BIN_CMD)
    touch(LIB_RS)
    lib_only_ms = run_ms(LIB_CMD)
    bin_after_lib_ms = run_ms(BIN_CMD)
    result = {
        'baseline_bin_ms': baseline_bin_ms,
        'lib_only_ms_after_touch_lib_rs': lib_only_ms,
        'bin_ms_after_lib_is_built': bin_after_lib_ms,
        'combined_ms': lib_only_ms + bin_after_lib_ms,
        'result': 'library_path_rebuild_time_is_split_into_os_node_library_compile_and_following_steelsearch_binary_compile',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
