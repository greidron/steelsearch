#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
CARGO_TAG = '0.77.0'
CARGO_REPO = 'https://github.com/rust-lang/cargo.git'


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


def clone_cargo_source(base: Path) -> Path:
    dst = base / 'cargo-src'
    run(['git', 'clone', '--depth', '1', '--branch', CARGO_TAG, CARGO_REPO, str(dst)], cwd=base)
    return dst


def parse_unit_data(html_path: Path):
    text = html_path.read_text()
    m = re.search(r'const UNIT_DATA = (.*?);\n', text, re.S)
    if not m:
        raise RuntimeError(f'UNIT_DATA not found in {html_path}')
    return json.loads(m.group(1))


def find_timings_html(target_dir: Path) -> Path:
    candidates = sorted((target_dir / 'cargo-timings').glob('cargo-timing*.html'))
    if not candidates:
        raise RuntimeError(f'no cargo timing html in {target_dir / "cargo-timings"}')
    return candidates[-1]


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_check_bin_fixture(root: Path) -> Path:
    ws = root / 'check_bin'
    write(ws / 'Cargo.toml', '[workspace]\nmembers = ["producer", "consumer"]\nresolver = "2"\n')
    write(ws / 'producer/Cargo.toml', '[package]\nname = "producer"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n')
    write(ws / 'producer/src/lib.rs', 'pub fn meaning() -> u32 { 42 }\n')
    write(ws / 'consumer/Cargo.toml', '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\nproducer = { path = "../producer" }\n')
    write(ws / 'consumer/src/main.rs', 'fn main() { println!("{}", producer::meaning()); }\n')
    return ws


def make_build_lib_fixture(root: Path) -> Path:
    ws = root / 'build_lib'
    write(ws / 'Cargo.toml', '[workspace]\nmembers = ["producer", "consumer"]\nresolver = "2"\n')
    write(ws / 'producer/Cargo.toml', '[package]\nname = "producer"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n')
    write(ws / 'producer/src/lib.rs', 'pub fn meaning() -> u32 { 42 }\n')
    write(ws / 'consumer/Cargo.toml', '[package]\nname = "consumer"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n\n[dependencies]\nproducer = { path = "../producer" }\n')
    write(ws / 'consumer/src/lib.rs', 'pub fn use_it() -> u32 { producer::meaning() }\n')
    return ws


def run_check_fixture(ws: Path):
    env = dict(os.environ)
    env['CARGO_TERM_COLOR'] = 'never'
    subprocess.run(['cargo', 'clean'], cwd=ws, env=env, text=True, capture_output=True, check=True)
    subprocess.run(['cargo', 'check', '--timings', '--workspace'], cwd=ws, env=env, text=True, capture_output=True, check=True)
    units = parse_unit_data(find_timings_html(ws / 'target'))
    producer = next(u for u in units if u['name'] == 'producer')
    return {
        'target': producer['target'],
        'rmeta_time': producer.get('rmeta_time'),
        'unlocked_units_len': len(producer.get('unlocked_units', [])),
        'unlocked_rmeta_units_len': len(producer.get('unlocked_rmeta_units', [])),
        'unlocked_units': producer.get('unlocked_units', []),
        'unlocked_rmeta_units': producer.get('unlocked_rmeta_units', []),
    }


def run_build_fixture(ws: Path):
    env = dict(os.environ)
    env['CARGO_TERM_COLOR'] = 'never'
    subprocess.run(['cargo', 'clean'], cwd=ws, env=env, text=True, capture_output=True, check=True)
    subprocess.run(['cargo', 'build', '--timings', '--workspace'], cwd=ws, env=env, text=True, capture_output=True, check=True)
    units = parse_unit_data(find_timings_html(ws / 'target'))
    producer = next(u for u in units if u['name'] == 'producer' and u['target'] == '')
    consumer_index = next(i for i, u in enumerate(units) if u['name'] == 'consumer' and u['target'] == '')
    return {
        'target': producer['target'],
        'rmeta_time': producer.get('rmeta_time'),
        'unlocked_units_len': len(producer.get('unlocked_units', [])),
        'unlocked_rmeta_units_len': len(producer.get('unlocked_rmeta_units', [])),
        'unlocked_units': producer.get('unlocked_units', []),
        'unlocked_rmeta_units': producer.get('unlocked_rmeta_units', []),
        'consumer_index': consumer_index,
        'consumer_unlocked_by_rmeta': consumer_index in producer.get('unlocked_rmeta_units', []),
    }


def main():
    with tempfile.TemporaryDirectory(prefix='cargo-unlocked-rmeta-') as td:
        base = Path(td)
        cargo_src = clone_cargo_source(base)
        context_rs = (cargo_src / 'src/cargo/core/compiler/context/mod.rs').read_text()
        queue_rs = (cargo_src / 'src/cargo/core/compiler/job_queue/mod.rs').read_text()
        timings_rs = (cargo_src / 'src/cargo/core/compiler/timings.rs').read_text()

        only_requires_rmeta_has_build_parent = '&& parent.mode == CompileMode::Build' in context_rs
        only_requires_rmeta_has_build_dep = '&& dep.mode == CompileMode::Build' in context_rs
        only_requires_rmeta_checks_no_upstream_objects_parent = '!parent.requires_upstream_objects()' in context_rs
        only_requires_rmeta_checks_no_upstream_objects_dep = '!dep.requires_upstream_objects()' in context_rs
        metadata_edge_created_from_only_requires_rmeta = 'if cx.only_requires_rmeta(unit, &dep.unit)' in queue_rs and 'Artifact::Metadata' in queue_rs
        timings_record_unlocked_rmeta_on_metadata_finish = 'unit_rmeta_finished(&mut self, id: JobId, unlocked: Vec<&Unit>)' in timings_rs and '.unlocked_rmeta_units' in timings_rs

        check_ws = make_check_bin_fixture(base)
        build_ws = make_build_lib_fixture(base)
        check_result = run_check_fixture(check_ws)
        build_result = run_build_fixture(build_ws)

        result = {
            'cargo_tag': CARGO_TAG,
            'source_only_requires_rmeta_has_build_parent': only_requires_rmeta_has_build_parent,
            'source_only_requires_rmeta_has_build_dep': only_requires_rmeta_has_build_dep,
            'source_only_requires_rmeta_checks_no_upstream_objects_parent': only_requires_rmeta_checks_no_upstream_objects_parent,
            'source_only_requires_rmeta_checks_no_upstream_objects_dep': only_requires_rmeta_checks_no_upstream_objects_dep,
            'source_metadata_edge_created_from_only_requires_rmeta': metadata_edge_created_from_only_requires_rmeta,
            'source_timings_record_unlocked_rmeta_on_metadata_finish': timings_record_unlocked_rmeta_on_metadata_finish,
            'check_bin_fixture': check_result,
            'build_lib_fixture': build_result,
            'result': 'unlocked_rmeta_units_are_populated_only_for_build_mode_rlib_to_rlib_edges_and_not_for_check_or_bin_consumer_graphs',
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
