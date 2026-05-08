#!/usr/bin/env python3
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
MAIN_RS = ROOT / 'crates/os-node/src/main.rs'
CMD = [
    'cargo','build','-vv','-p','os-node','--features','standalone-runtime','--bin','steelsearch','--manifest-path',str(ROOT / 'Cargo.toml')
]
DIRTY_RE = re.compile(r'\bDirty ([^ ]+) v')
COMPILING_RE = re.compile(r'\bCompiling ([^ ]+) v')
FRESH_RE = re.compile(r'\bFresh ([^ ]+) v')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    touch(MAIN_RS)
    cp = subprocess.run(CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        print(cp.stdout)
        print(cp.stderr, file=sys.stderr)
        return cp.returncode
    combined = cp.stdout + '\n' + cp.stderr
    dirty = sorted(set(DIRTY_RE.findall(combined)))
    compiling = sorted(set(COMPILING_RE.findall(combined)))
    fresh = sorted(set(FRESH_RE.findall(combined)))
    result = {
        'dirty_crates': dirty,
        'compiling_crates': compiling,
        'fresh_crates_sample_count': len(fresh),
        'result': 'incremental_rebuild_scope_after_touching_main_rs_is_observed_via_cargo_build_vv',
    }
    print(json.dumps(result, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
