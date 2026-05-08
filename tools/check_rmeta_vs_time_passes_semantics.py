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
NIGHTLY_TIMINGS_CMD = [
    'cargo', '+nightly', 'build', '--timings',
    '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--bin', 'steelsearch',
    '--manifest-path', str(ROOT / 'Cargo.toml'),
]
NIGHTLY_TIME_PASSES_CMD = [
    'cargo', '+nightly', 'rustc',
    '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--lib',
    '--manifest-path', str(ROOT / 'Cargo.toml'),
    '--', '-Z', 'time-passes',
]
UNIT_DATA_RE = re.compile(r'const\s+UNIT_DATA\s*=\s*(\[.*?\]);', re.S)
TIME_RE = re.compile(r'^time:\s+([0-9.]+);.*\t([A-Za-z0-9_]+)$')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def newest_timing_html(before: set[Path]) -> Path:
    after = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    new_files = sorted(after - before, key=lambda p: p.stat().st_mtime)
    if new_files:
        return new_files[-1]
    return max(after, key=lambda p: p.stat().st_mtime)


def run_nightly_timings() -> dict:
    before = set(TIMINGS_DIR.glob('cargo-timing-*.html'))
    cp = subprocess.run(NIGHTLY_TIMINGS_CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    html = newest_timing_html(before)
    text = html.read_text()
    unit_data = json.loads(UNIT_DATA_RE.search(text).group(1))
    lib_unit = next(unit for unit in unit_data if unit['name'] == 'os-node' and unit['target'] == '')
    bin_unit = next(unit for unit in unit_data if unit['name'] == 'os-node' and 'steelsearch' in unit['target'])
    sections = {name: payload for name, payload in (lib_unit.get('sections') or [])}
    frontend = sections.get('frontend')
    codegen = sections.get('codegen')
    return {
        'timing_html': str(html),
        'lib_duration_s': lib_unit['duration'],
        'lib_frontend_s': None if frontend is None else round(frontend['end'] - frontend['start'], 3),
        'lib_codegen_s': None if codegen is None else round(codegen['end'] - codegen['start'], 3),
        'bin_duration_s': bin_unit['duration'],
    }


def run_nightly_time_passes() -> dict:
    cp = subprocess.run(NIGHTLY_TIME_PASSES_CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    phases = []
    for line in cp.stderr.splitlines():
        m = TIME_RE.match(line.strip())
        if m:
            phases.append((m.group(2), float(m.group(1))))
    phase_map = {phase: seconds for phase, seconds in phases}
    return {
        'codegen_crate_s': phase_map.get('codegen_crate'),
        'llvm_passes_s': phase_map.get('LLVM_passes'),
        'codegen_to_llvm_ir_s': phase_map.get('codegen_to_LLVM_IR'),
        'generate_crate_metadata_s': phase_map.get('generate_crate_metadata'),
        'total_s': phase_map.get('total'),
    }


def main() -> int:
    touch(LIB_RS)
    timings = run_nightly_timings()
    touch(LIB_RS)
    time_passes = run_nightly_time_passes()

    result = {
        'nightly_timings': timings,
        'nightly_time_passes': time_passes,
        'same_toolchain_but_different_story': (
            timings['lib_codegen_s'] > timings['lib_frontend_s']
            and time_passes['codegen_crate_s'] > time_passes['generate_crate_metadata_s']
            and time_passes['llvm_passes_s'] > time_passes['generate_crate_metadata_s']
        ),
        'result': 'the_gap_is_best_explained_by_measurement_semantics_and_build_target_difference_nightly_cargo_timings_splits_the_incremental_lib_unit_into_frontend_and_codegen_sections_while_time_passes_reports_full_library_compile_phases_where_codegen_and_llvm_dominate_metadata',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
