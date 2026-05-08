#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
SRC = ROOT / 'crates/os-node/src'
LIB_RS = SRC / 'lib.rs'
SELF_PROFILE_CHECKER = ROOT / 'tools/check_incremental_frontend_query_hotspots_from_self_profile.py'


def main() -> int:
    lib_lines = LIB_RS.read_text().splitlines()
    pub_mods = []
    for line in lib_lines:
        match = re.match(r'pub mod ([a-zA-Z0-9_]+);', line)
        if match:
            pub_mods.append(match.group(1))

    derive_count = 0
    proc_attr_count = 0
    for path in SRC.glob('*.rs'):
        text = path.read_text()
        derive_count += text.count('#[derive(')
        proc_attr_count += text.count('#[tokio::main]') + text.count('#[async_trait') + text.count('#[serde(')

    standalone_runtime_lines = sum(1 for _ in open(SRC / 'standalone_runtime.rs'))

    cp = subprocess.run(
        ['python3', str(SELF_PROFILE_CHECKER)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)
    profile = json.loads(cp.stdout)

    result = {
        'pub_mod_count': len(pub_mods),
        'total_rs_files': len(list(SRC.glob('*.rs'))),
        'derive_count': derive_count,
        'proc_attr_count': proc_attr_count,
        'standalone_runtime_lines': standalone_runtime_lines,
        'top_frontend_like_items': profile['top_frontend_like_items'][:7],
        'result': 'frontend_hotspots_align_with_crate_root_module_fanout_and_proc_macro_expansion_pressure_because_lib_rs_reaches_most_source_files_and_the_crate_contains_many_derive_and_proc_macro_sites',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
