#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
CHECKERS = {
    'rebuild_costs': ROOT / 'tools/check_os_node_source_file_rebuild_costs.py',
    'compile_units': ROOT / 'tools/check_os_node_compile_units_by_touched_file.py',
    'lib_vs_bin': ROOT / 'tools/check_os_node_lib_vs_bin_time_contribution.py',
}


def load_json_from_script(path: Path) -> dict:
    cp = subprocess.run(
        ['python3', str(path)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    return json.loads(cp.stdout)


def main() -> int:
    lib_text = LIB_RS.read_text()
    pub_mod_count = sum(1 for line in lib_text.splitlines() if line.startswith('pub mod '))
    pub_use_count = sum(1 for line in lib_text.splitlines() if line.startswith('pub use '))
    has_standalone_reexport = 'pub use standalone_runtime::*;' in lib_text

    rebuild_costs = load_json_from_script(CHECKERS['rebuild_costs'])
    compile_units = load_json_from_script(CHECKERS['compile_units'])
    lib_vs_bin = load_json_from_script(CHECKERS['lib_vs_bin'])

    file_costs = rebuild_costs['file_rebuild_cost_ms']
    units = compile_units['compile_units_by_file']

    result = {
        'pub_mod_count': pub_mod_count,
        'pub_use_count': pub_use_count,
        'has_standalone_reexport': has_standalone_reexport,
        'file_rebuild_cost_ms': file_costs,
        'compile_units_by_file': units,
        'lib_only_ms_after_touch_lib_rs': lib_vs_bin['lib_only_ms_after_touch_lib_rs'],
        'bin_ms_after_lib_is_built': lib_vs_bin['bin_ms_after_lib_is_built'],
        'lib_path_costlier_than_main': (
            file_costs['lib.rs'] > file_costs['main.rs']
            and file_costs['standalone_runtime.rs'] > file_costs['main.rs']
        ),
        'main_is_binary_only': units['main.rs'] == ['steelsearch'],
        'lib_paths_hit_library_and_binary': (
            units['lib.rs'] == ['os_node', 'steelsearch']
            and units['standalone_runtime.rs'] == ['os_node', 'steelsearch']
        ),
        'library_compile_dominates_binary_compile': (
            lib_vs_bin['lib_only_ms_after_touch_lib_rs'] > lib_vs_bin['bin_ms_after_lib_is_built']
        ),
        'result': 'lib_rs_and_standalone_runtime_rs_cost_more_than_main_rs_because_they_invalidate_the_broad_os_node_library_export_surface_and_force_dual_target_recompilation',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
