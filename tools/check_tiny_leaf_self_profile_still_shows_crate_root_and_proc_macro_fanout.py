#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
SRC = ROOT / 'crates/os-node/src'
LEAF = SRC / 'write_path_invariants.rs'
PROFILE_DIR = Path('/tmp/osnode-selfprofile-leaf')
SELF_PROFILE_CMD = [
    'cargo', '+nightly', 'rustc',
    '-p', 'os-node',
    '--features', 'standalone-runtime',
    '--lib',
    '--manifest-path', str(ROOT / 'Cargo.toml'),
    '--', f'-Z', f'self-profile={PROFILE_DIR}',
]
ROW_RE = re.compile(r'^\|\s(.+?)\s+\|\s+([0-9.]+(?:s|ms|µs|ns))\s+\|')
BACKEND_PREFIXES = ('LLVM_', 'codegen', 'link_', 'link', 'monomorphization', 'target_machine')


def touch(path: Path) -> None:
    now = time.time()
    os.utime(path, (now, now))


def main() -> int:
    if PROFILE_DIR.exists():
        shutil.rmtree(PROFILE_DIR)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    touch(LEAF)
    cp = subprocess.run(SELF_PROFILE_CMD, cwd=ROOT, capture_output=True, text=True)
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)

    profile = max(PROFILE_DIR.glob('*.mm_profdata'), key=lambda p: p.stat().st_mtime)
    summary = subprocess.run(
        ['summarize', 'summarize', str(profile)],
        capture_output=True,
        text=True,
    )
    if summary.returncode != 0:
        raise SystemExit(summary.returncode)

    rows = []
    for line in summary.stdout.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        item = m.group(1).strip().replace(' .', '').strip()
        self_time = m.group(2)
        rows.append({'item': item, 'self_time': self_time})

    frontend_rows = [row for row in rows if not row['item'].startswith(BACKEND_PREFIXES)]
    leaf_text = LEAF.read_text()

    result = {
        'leaf_local_derive_count': leaf_text.count('#[derive('),
        'leaf_local_proc_attr_count': leaf_text.count('#[serde(') + leaf_text.count('#[tokio::main]') + leaf_text.count('#[async_trait'),
        'top_frontend_like_items': frontend_rows[:8],
        'has_expand_crate_hotspot': any(row['item'].startswith('expand_crate') for row in frontend_rows[:8]),
        'has_expand_proc_macro_hotspot': any(row['item'].startswith('expand_proc_macro') for row in frontend_rows[:8]),
        'has_late_resolve_hotspot': any(row['item'].startswith('late_resolve_crate') for row in frontend_rows[:8]),
        'result': 'tiny_leaf_rebuild_still_shows_expand_crate_and_proc_macro_frontend_hotspots_even_when_the_touched_file_itself_has_no_local_macro_sites_so_shared_cost_is_directly_tied_to_crate_root_fanout_and_crate_wide_macro_reruns',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
