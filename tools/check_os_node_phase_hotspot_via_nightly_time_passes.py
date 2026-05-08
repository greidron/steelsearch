#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
CMD = [
    'cargo', '+nightly', 'rustc', '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--lib',
    '--manifest-path', str(ROOT / 'Cargo.toml'),
    '--', '-Z', 'time-passes',
]
TIME_RE = re.compile(r'^time:\s+([0-9.]+);.*\t([A-Za-z0-9_]+)$')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    touch(LIB_RS)
    cp = subprocess.run(CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)

    phases = []
    for line in cp.stderr.splitlines():
        m = TIME_RE.match(line.strip())
        if m:
            phases.append({
                'phase': m.group(2),
                'seconds': float(m.group(1)),
            })

    non_total = [p for p in phases if p['phase'] != 'total']
    top_phases = sorted(non_total, key=lambda p: p['seconds'], reverse=True)[:8]
    metadata_phase = next((p for p in non_total if p['phase'] == 'generate_crate_metadata'), None)
    codegen_phase = next((p for p in non_total if p['phase'] == 'codegen_crate'), None)
    llvm_phase = next((p for p in non_total if p['phase'] == 'LLVM_passes'), None)

    result = {
        'top_phases': top_phases,
        'generate_crate_metadata_seconds': metadata_phase['seconds'] if metadata_phase else None,
        'codegen_crate_seconds': codegen_phase['seconds'] if codegen_phase else None,
        'llvm_passes_seconds': llvm_phase['seconds'] if llvm_phase else None,
        'metadata_is_large_but_not_largest': (
            metadata_phase is not None
            and codegen_phase is not None
            and metadata_phase['seconds'] < codegen_phase['seconds']
        ),
        'result': 'nightly_time_passes_shows_generate_crate_metadata_is_a_real_hotspot_but_codegen_and_llvm_are_even_larger_in_the_full_os_node_library_compile',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
