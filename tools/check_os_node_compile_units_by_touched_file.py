#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
CMD = [
    'cargo','build','-vv','-p','os-node','--features','standalone-runtime','--bin','steelsearch','--manifest-path',str(ROOT / 'Cargo.toml')
]
FILES = [
    ROOT / 'crates/os-node/src/main.rs',
    ROOT / 'crates/os-node/src/lib.rs',
    ROOT / 'crates/os-node/src/standalone_runtime.rs',
]
CRATE_RE = re.compile(r'--crate-name\s+([^\s]+)')
RUNNING_RE = re.compile(r'Running `([^`]+)`')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    result = {}
    for path in FILES:
        touch(path)
        cp = subprocess.run(CMD, cwd=ROOT, capture_output=True, text=True)
        if cp.returncode != 0:
            raise SystemExit(cp.returncode)
        combined = cp.stdout + '\n' + cp.stderr
        crate_names = []
        for m in RUNNING_RE.finditer(combined):
            cmd = m.group(1)
            crate = CRATE_RE.search(cmd)
            if crate:
                crate_names.append(crate.group(1))
        result[path.name] = crate_names
    print(json.dumps({
        'compile_units_by_file': result,
        'result': 'cargo_build_vv_reveals_binary_only_vs_library_path_compile_unit_difference',
    }, indent=2))
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
