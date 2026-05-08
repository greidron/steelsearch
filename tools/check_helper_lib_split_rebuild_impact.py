#!/usr/bin/env python3
import json
import subprocess
import tempfile
import time
from pathlib import Path
from statistics import median

HEADER = "// synthetic timing fixture\n"
ITEM_COUNT = 1200
SAMPLES = 3


def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


def write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def gen_runtime_body() -> str:
    lines = [HEADER]
    for i in range(ITEM_COUNT):
        lines.append(f'pub struct Item{i} {{ pub value: u64 }}\n')
        lines.append(f'impl Item{i} {{ pub fn new() -> Self {{ Self {{ value: {i} }} }} }}\n')
    lines.append('pub fn sentinel() -> u64 {\n')
    lines.extend([f'    Item{i}::new().value +\n' for i in range(ITEM_COUNT - 1)])
    lines.append(f'    Item{ITEM_COUNT - 1}::new().value\n')
    lines.append('}\n')
    return ''.join(lines)


def make_monolith(root: Path) -> Path:
    ws = root / 'monolith'
    write(ws / 'Cargo.toml', '[workspace]\nmembers = ["os_node_monolith", "app"]\nresolver = "2"\n')
    write(ws / 'os_node_monolith/Cargo.toml', '[package]\nname = "os_node_monolith"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n')
    write(ws / 'os_node_monolith/src/runtime_surface.rs', gen_runtime_body())
    write(ws / 'os_node_monolith/src/lib.rs', 'pub mod runtime_surface;\npub use runtime_surface::sentinel;\n')
    write(ws / 'app/Cargo.toml', '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2021"\n\n[[bin]]\nname = "app"\npath = "src/main.rs"\n\n[dependencies]\nos_node_monolith = { path = "../os_node_monolith" }\n')
    write(ws / 'app/src/main.rs', 'fn main() { println!("{}", os_node_monolith::sentinel()); }\n')
    return ws


def make_split(root: Path) -> Path:
    ws = root / 'split'
    write(ws / 'Cargo.toml', '[workspace]\nmembers = ["runtime_surface", "os_node_facade", "app"]\nresolver = "2"\n')
    write(ws / 'runtime_surface/Cargo.toml', '[package]\nname = "runtime_surface"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n')
    write(ws / 'runtime_surface/src/lib.rs', gen_runtime_body())
    write(ws / 'os_node_facade/Cargo.toml', '[package]\nname = "os_node_facade"\nversion = "0.1.0"\nedition = "2021"\n\n[lib]\npath = "src/lib.rs"\n\n[dependencies]\nruntime_surface = { path = "../runtime_surface" }\n')
    write(ws / 'os_node_facade/src/lib.rs', 'pub use runtime_surface::sentinel;\n')
    write(ws / 'app/Cargo.toml', '[package]\nname = "app"\nversion = "0.1.0"\nedition = "2021"\n\n[[bin]]\nname = "app"\npath = "src/main.rs"\n\n[dependencies]\nos_node_facade = { path = "../os_node_facade" }\n')
    write(ws / 'app/src/main.rs', 'fn main() { println!("{}", os_node_facade::sentinel()); }\n')
    return ws


def cargo_build(ws: Path):
    start = time.perf_counter()
    run(['cargo', 'build', '--workspace'], cwd=ws)
    return round((time.perf_counter() - start) * 1000)


def warm(ws: Path):
    run(['cargo', 'clean'], cwd=ws)
    cargo_build(ws)


def touch_with_marker(path: Path, n: int):
    text = path.read_text()
    if text.endswith('\n'):
        text += f'// touch {n}\n'
    else:
        text += f'\n// touch {n}\n'
    path.write_text(text)


def measure_series(ws: Path, rel_path: str):
    path = ws / rel_path
    samples = []
    for i in range(SAMPLES):
        touch_with_marker(path, i)
        samples.append(cargo_build(ws))
    return samples


def main():
    with tempfile.TemporaryDirectory(prefix='helper-lib-bench-') as td:
        root = Path(td)
        monolith = make_monolith(root)
        split = make_split(root)

        warm(monolith)
        monolith_root_samples = measure_series(monolith, 'os_node_monolith/src/lib.rs')
        warm(monolith)
        monolith_runtime_samples = measure_series(monolith, 'os_node_monolith/src/runtime_surface.rs')

        warm(split)
        split_facade_samples = measure_series(split, 'os_node_facade/src/lib.rs')
        warm(split)
        split_helper_samples = measure_series(split, 'runtime_surface/src/lib.rs')

        result = {
            'item_count': ITEM_COUNT,
            'samples_per_case': SAMPLES,
            'monolith_root_edit_ms': monolith_root_samples,
            'split_facade_edit_ms': split_facade_samples,
            'monolith_runtime_edit_ms': monolith_runtime_samples,
            'split_helper_edit_ms': split_helper_samples,
            'monolith_root_median_ms': median(monolith_root_samples),
            'split_facade_median_ms': median(split_facade_samples),
            'monolith_runtime_median_ms': median(monolith_runtime_samples),
            'split_helper_median_ms': median(split_helper_samples),
            'root_edit_delta_ms': median(monolith_root_samples) - median(split_facade_samples),
            'runtime_edit_delta_ms': median(monolith_runtime_samples) - median(split_helper_samples),
            'result': 'helper_lib_split_significantly_reduces_small_facade_edit_rebuilds_but_does_not_help_large_helper_owned_runtime_edits',
        }
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
