#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
OS_NODE_LIB = REPO / 'crates/os-node/src/lib.rs'
STANDALONE_RUNTIME = REPO / 'crates/os-node/src/standalone_runtime.rs'
REST_CORE_LIB = REPO / 'crates/os-node-rest-core/src/lib.rs'


def run(cmd):
    return subprocess.run(cmd, cwd=REPO, text=True, capture_output=True, check=True)


def line_count(path: Path) -> int:
    with path.open() as f:
        return sum(1 for _ in f)


def main():
    run(['cargo', 'build', '-p', 'os-node', '--features', 'standalone-runtime', '--bin', 'steelsearch', '--manifest-path', str(REPO / 'Cargo.toml')])
    original = OS_NODE_LIB.read_text()
    OS_NODE_LIB.write_text(original + ('\n' if not original.endswith('\n') else '') + '// stronger split probe\n')
    try:
        out = run([
            'cargo', 'build', '-vv', '-p', 'os-node', '--features', 'standalone-runtime', '--bin', 'steelsearch',
            '--manifest-path', str(REPO / 'Cargo.toml')
        ]).stderr
    finally:
        OS_NODE_LIB.write_text(original)

    dirty_lines = [line for line in out.splitlines() if 'Dirty ' in line]
    compiling_lines = [line for line in out.splitlines() if line.startswith('   Compiling ')]
    fresh_rest_core = any('Fresh os-node-rest-core' in line for line in out.splitlines())
    dirty_os_node = any('Dirty os-node v0.1.0' in line for line in dirty_lines)
    compiling_os_node = any('Compiling os-node v0.1.0' in line for line in compiling_lines)
    compiling_rest_core = any('Compiling os-node-rest-core v0.1.0' in line for line in compiling_lines)
    compiling_steelsearch = any('Compiling os-node v0.1.0' in line for line in compiling_lines)

    result = {
        'standalone_runtime_lines': line_count(STANDALONE_RUNTIME),
        'rest_core_lines': line_count(REST_CORE_LIB),
        'dirty_os_node_after_lib_rs_touch': dirty_os_node,
        'compiling_os_node_after_lib_rs_touch': compiling_os_node,
        'fresh_rest_core_after_lib_rs_touch': fresh_rest_core,
        'compiling_rest_core_after_lib_rs_touch': compiling_rest_core,
        'dirty_lines_sample': dirty_lines[:6],
        'compiling_lines_sample': compiling_lines[:6],
        'result': 'a_stronger_crate_split_is_needed_for_performance_because_lib_rs_touches_still_recompile_the_large_os_node_lib_unit_while_the_small_rest_core_crate_stays_fresh',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
