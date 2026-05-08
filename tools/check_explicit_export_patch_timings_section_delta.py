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
TIMINGS_DIR = ROOT / 'target/cargo-timings'
BUILD_CMD = [
    'cargo', 'build', '--timings',
    '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--bin', 'steelsearch',
    '--manifest-path', str(ROOT / 'Cargo.toml')
]
UNIT_DATA_RE = re.compile(r'const\s+UNIT_DATA\s*=\s*(\[.*?\]);', re.S)


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def profile_mode(lib_text: str) -> dict:
    LIB_RS.write_text(lib_text)
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    touch(LEAF)
    before = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    subprocess.run(BUILD_CMD, cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    html = newest_timing_html(before)
    text = html.read_text()
    unit_data = json.loads(UNIT_DATA_RE.search(text).group(1))
    lib_unit = next(unit for unit in unit_data if unit['name'] == 'os-node' and unit['target'] == '')
    return {
        'lib_duration_s': lib_unit['duration'],
        'rmeta_s': lib_unit['rmeta_time'],
        'post_rmeta_codegen_s': round(lib_unit['duration'] - lib_unit['rmeta_time'], 3),
    }


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
        star_profile = profile_mode(star)
        explicit_profile = profile_mode(original)
    finally:
        LIB_RS.write_text(original)

    result = {
        'star_profile': star_profile,
        'explicit_profile': explicit_profile,
        'delta_explicit_minus_star_ms': {
            'lib_duration_ms': round((explicit_profile['lib_duration_s'] - star_profile['lib_duration_s']) * 1000, 2),
            'rmeta_ms': round((explicit_profile['rmeta_s'] - star_profile['rmeta_s']) * 1000, 2),
            'post_rmeta_codegen_ms': round((explicit_profile['post_rmeta_codegen_s'] - star_profile['post_rmeta_codegen_s']) * 1000, 2),
        },
        'result': 'stable_cargo_timings_rmeta_vs_post_rmeta_delta_compared_between_star_and_explicit_reexport_modes',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
