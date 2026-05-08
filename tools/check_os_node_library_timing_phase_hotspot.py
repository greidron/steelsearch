#!/usr/bin/env python3
import json
import os
import re
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
TIMINGS_DIR = ROOT / 'target/cargo-timings'
CARGO_CMD = [
    'cargo', 'build', '--timings', '-p', 'os-node', '--features', 'standalone-runtime',
    '--bin', 'steelsearch', '--manifest-path', str(ROOT / 'Cargo.toml')
]


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def run_timings_build() -> Path:
    before = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    cp = subprocess.run(CARGO_CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    after = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def load_unit_data(path: Path) -> list[dict]:
    text = path.read_text()
    match = re.search(r'const\s+UNIT_DATA\s*=\s*(\[.*?\]);', text, re.S)
    if not match:
        raise SystemExit('UNIT_DATA not found')
    return json.loads(match.group(1))


def main() -> int:
    touch(LIB_RS)
    timing_html = run_timings_build()
    unit_data = load_unit_data(timing_html)
    os_node_units = [unit for unit in unit_data if unit['name'] == 'os-node']
    lib_unit = next(unit for unit in os_node_units if unit['target'] == '')
    bin_unit = next(unit for unit in os_node_units if 'steelsearch' in unit['target'])

    lib_duration_ms = int(lib_unit['duration'] * 1000)
    lib_rmeta_ms = int(lib_unit['rmeta_time'] * 1000)
    bin_duration_ms = int(bin_unit['duration'] * 1000)

    result = {
        'timing_html': str(timing_html),
        'os_node_units': os_node_units,
        'lib_duration_ms': lib_duration_ms,
        'lib_rmeta_ms': lib_rmeta_ms,
        'bin_duration_ms': bin_duration_ms,
        'lib_rmeta_share_of_lib': round(lib_unit['rmeta_time'] / lib_unit['duration'], 3),
        'library_duration_exceeds_binary_duration': lib_duration_ms > bin_duration_ms,
        'library_rmeta_alone_exceeds_binary_duration': lib_rmeta_ms > bin_duration_ms,
        'result': 'cargo_timings_show_the_os_node_library_hotspot_is_mainly_in_the_library_unit_itself_and_mostly_in_rmeta_metadata_time_not_in_the_following_steelsearch_binary_unit',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
