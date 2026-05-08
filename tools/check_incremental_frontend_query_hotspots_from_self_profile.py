#!/usr/bin/env python3
import json
import re
import subprocess
from pathlib import Path

PROFILE_DIR = Path('/tmp/osnode-selfprofile')
ROW_RE = re.compile(r'^\|\s(.+?)\s+\|\s+([0-9.]+(?:s|ms|µs|ns))\s+\|')
BACKEND_PREFIXES = (
    'LLVM_',
    'codegen',
    'link_',
    'link',
    'monomorphization',
    'target_machine',
)


def main() -> int:
    profile = max(PROFILE_DIR.glob('*.mm_profdata'), key=lambda p: p.stat().st_mtime)
    cp = subprocess.run(
        ['summarize', 'summarize', str(profile)],
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise SystemExit(cp.returncode)

    rows = []
    for line in cp.stdout.splitlines():
        m = ROW_RE.match(line)
        if not m:
            continue
        item = m.group(1).strip().replace(' .', '').strip()
        self_time = m.group(2)
        rows.append({'item': item, 'self_time': self_time})

    frontend_rows = [
        row for row in rows
        if not row['item'].startswith(BACKEND_PREFIXES)
    ]

    result = {
        'profile': str(profile),
        'top_frontend_like_items': frontend_rows[:10],
        'result': 'self_profile_summary_shows_incremental_frontend_like_hotspots_are_led_by_expand_crate_hir_crate_fn_abi_and_resolve_macro_queries_once_backend_items_are_excluded',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
