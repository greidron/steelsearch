#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
LEAF = ROOT / 'crates/os-node/src/write_path_invariants.rs'
STAR_PROFILE_DIR = Path('/tmp/osnode-selfprofile-star')
EXPLICIT_PROFILE_DIR = Path('/tmp/osnode-selfprofile-explicit')
SELF_PROFILE_BASE_CMD = [
    'cargo', '+nightly', 'rustc',
    '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--lib',
    '--manifest-path', str(ROOT / 'Cargo.toml'),
    '--',
]
ROW_RE = re.compile(r'^\|\s(.+?)\s+\|\s+([0-9.]+)(s|ms|µs|ns)\s+\|')
ITEMS = [
    'expand_crate',
    'hir_crate',
    'expand_proc_macro',
    'late_resolve_crate',
    'incr_comp_encode_dep_graph',
]


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def to_ms(value: float, unit: str) -> float:
    if unit == 's':
        return value * 1000.0
    if unit == 'ms':
        return value
    if unit == 'µs':
        return value / 1000.0
    if unit == 'ns':
        return value / 1_000_000.0
    raise ValueError(unit)


def profile_mode(lib_text: str, profile_dir: Path) -> dict:
    if profile_dir.exists():
        shutil.rmtree(profile_dir)
    profile_dir.mkdir(parents=True, exist_ok=True)
    LIB_RS.write_text(lib_text)
    touch(LEAF)
    cmd = SELF_PROFILE_BASE_CMD + [f'-Z', f'self-profile={profile_dir}']
    cp = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    profile = max(profile_dir.glob('*.mm_profdata'), key=lambda p: p.stat().st_mtime)
    summary = subprocess.run(['summarize', 'summarize', str(profile)], capture_output=True, text=True)
    if summary.returncode != 0:
        raise SystemExit(summary.returncode)

    values = {}
    for line in summary.stdout.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        item = m.group(1).strip().replace(' .', '').strip()
        for wanted in ITEMS:
            if item.startswith(wanted):
                values[wanted] = round(to_ms(float(m.group(2)), m.group(3)), 2)
    return values


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
        star_values = profile_mode(star, STAR_PROFILE_DIR)
        explicit_values = profile_mode(original, EXPLICIT_PROFILE_DIR)
    finally:
        LIB_RS.write_text(original)

    deltas = {
        item: round(explicit_values[item] - star_values[item], 2)
        for item in ITEMS
        if item in star_values and item in explicit_values
    }

    result = {
        'star_frontend_items_ms': star_values,
        'explicit_frontend_items_ms': explicit_values,
        'delta_ms_explicit_minus_star': deltas,
        'largest_improvement_item': min(deltas, key=deltas.get) if deltas else None,
        'result': 'explicit_export_patch_frontend_hotspot_delta_compared_between_star_and_explicit_reexport_modes',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
