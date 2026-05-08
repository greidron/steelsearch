#!/usr/bin/env python3
import json
import re
import subprocess
import tempfile
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
HTML_RE = re.compile(r'const UNIT_DATA = (.*?);\n', re.S)


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


def parse_unit_data(html_path: Path):
    text = html_path.read_text()
    m = HTML_RE.search(text)
    if not m:
        raise RuntimeError(f'UNIT_DATA not found in {html_path}')
    return json.loads(m.group(1))


def latest_timing_html(target_dir: Path) -> Path:
    candidates = sorted((target_dir / 'cargo-timings').glob('cargo-timing*.html'))
    if not candidates:
        raise RuntimeError('no cargo timing html found')
    return candidates[-1]


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def make_fixture(root: Path) -> Path:
    ws = root / 'helper_refactor_fixture'
    write(ws / 'Cargo.toml', '[workspace]\nmembers = ["runtime_surface", "os_node_facade", "app"]\nresolver = "2"\n')

    write(ws / 'runtime_surface/Cargo.toml', '[package]\nname = "runtime_surface"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n')
    write(ws / 'runtime_surface/src/lib.rs', 'pub struct SteelNode;\npub fn serve() {}\n')

    write(ws / 'os_node_facade/Cargo.toml', '[package]\nname = "os_node_facade"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n\n[dependencies]\nruntime_surface = { path = "../runtime_surface" }\n')
    write(ws / 'os_node_facade/src/lib.rs', 'pub use runtime_surface::{serve, SteelNode};\n')

    write(ws / 'app/Cargo.toml', '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2021"\n\n[[bin]]\nname = "app"\npath = "src/main.rs"\n\n[dependencies]\nos_node_facade = { path = "../os_node_facade" }\n')
    write(ws / 'app/src/main.rs', 'fn main() { let _ = os_node_facade::SteelNode; os_node_facade::serve(); }\n')
    return ws


def main():
    lib_rs = (REPO / 'crates/os-node/src/lib.rs').read_text()
    has_standalone_runtime_module = 'pub mod standalone_runtime;' in lib_rs
    has_standalone_runtime_reexport = 'pub use standalone_runtime::' in lib_rs

    with tempfile.TemporaryDirectory(prefix='helper-lib-edge-') as td:
        ws = make_fixture(Path(td))
        run(['cargo', 'clean'], cwd=ws)
        run(['cargo', 'build', '--timings', '--workspace'], cwd=ws)
        units = parse_unit_data(latest_timing_html(ws / 'target'))

        runtime_idx = next(i for i, u in enumerate(units) if u['name'] == 'runtime_surface' and u['target'] == '')
        facade_idx = next(i for i, u in enumerate(units) if u['name'] == 'os_node_facade' and u['target'] == '')
        app_idx = next(i for i, u in enumerate(units) if u['name'] == 'app' and 'bin "app"' in u['target'])

        runtime_unit = units[runtime_idx]
        facade_unit = units[facade_idx]

        result = {
            'current_os_node_lib_has_standalone_runtime_module': has_standalone_runtime_module,
            'current_os_node_lib_has_standalone_runtime_reexport': has_standalone_runtime_reexport,
            'fixture_runtime_surface_unlocked_rmeta_units': runtime_unit.get('unlocked_rmeta_units', []),
            'fixture_runtime_surface_unlocked_units': runtime_unit.get('unlocked_units', []),
            'fixture_runtime_surface_unlocks_facade_by_rmeta': facade_idx in runtime_unit.get('unlocked_rmeta_units', []),
            'fixture_runtime_surface_does_not_unlock_app_by_rmeta': app_idx not in runtime_unit.get('unlocked_rmeta_units', []),
            'fixture_facade_unlocked_units': facade_unit.get('unlocked_units', []),
            'fixture_facade_unlocks_app_at_finish': app_idx in facade_unit.get('unlocked_units', []),
            'result': 'splitting_standalone_runtime_like_surface_into_a_helper_library_beneath_a_facade_library_creates_the_build_mode_rlib_to_rlib_edge_that_populates_unlocked_rmeta_units',
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
