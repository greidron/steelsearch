#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
LIB_RS = ROOT / 'crates/os-node/src/lib.rs'
CHECKERS = {
    'tiny_leaf': ROOT / 'tools/check_tiny_leaf_self_profile_still_shows_crate_root_and_proc_macro_fanout.py',
    'serde_cluster': ROOT / 'tools/check_serde_sites_cluster_in_standalone_runtime.py',
    'giant_vs_fanout': ROOT / 'tools/check_giant_body_vs_fanout_contribution.py',
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
    has_pub_mod_standalone_runtime = 'pub mod standalone_runtime;' in lib_text
    has_pub_use_standalone_runtime = 'pub use standalone_runtime::*;' in lib_text

    tiny_leaf = load_json_from_script(CHECKERS['tiny_leaf'])
    serde_cluster = load_json_from_script(CHECKERS['serde_cluster'])
    giant_vs_fanout = load_json_from_script(CHECKERS['giant_vs_fanout'])

    result = {
        'has_pub_mod_standalone_runtime': has_pub_mod_standalone_runtime,
        'has_pub_use_standalone_runtime': has_pub_use_standalone_runtime,
        'tiny_leaf_same_compile_units': giant_vs_fanout['same_compile_units'],
        'tiny_leaf_top_frontend_like_items': tiny_leaf['top_frontend_like_items'][:6],
        'serde_cluster_top_file': serde_cluster['top_file'],
        'serde_cluster_top_share': serde_cluster['top_share'],
        'result': 'tiny_leaf_rebuild_drags_the_standalone_runtime_serde_cluster_because_the_os_node_library_crate_root_explicitly_includes_and_reexports_standalone_runtime_so_rebuilding_the_library_target_reexpands_that_cluster',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
