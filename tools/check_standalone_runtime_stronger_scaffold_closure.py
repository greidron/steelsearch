#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
SRC = REPO / 'crates/os-node/src'
STANDALONE = SRC / 'standalone_runtime.rs'
USE_CRATE_RE = re.compile(r'^use crate::([A-Za-z0-9_]+);$', re.M)


def line_count(path: Path) -> int:
    with path.open() as f:
        return sum(1 for _ in f)


def main():
    text = STANDALONE.read_text()
    local_imports = sorted(set(USE_CRATE_RE.findall(text)))
    route_modules = sorted([name for name in local_imports if name.endswith('_route_registration')])
    support_items = sorted([name for name in local_imports if not name.endswith('_route_registration')])

    route_files = [SRC / f'{name}.rs' for name in route_modules]
    route_line_counts = {path.name: line_count(path) for path in route_files}
    support_resolution = {}
    for name in support_items:
        if (SRC / f'{name}.rs').exists():
            support_resolution[name] = f'file:{name}.rs'
        else:
            support_resolution[name] = 'item-in-lib-or-other-module'

    result = {
        'standalone_runtime_lines': line_count(STANDALONE),
        'local_import_count': len(local_imports),
        'route_module_count': len(route_modules),
        'support_item_count': len(support_items),
        'route_modules': route_modules,
        'support_items': support_items,
        'route_module_line_counts': route_line_counts,
        'route_module_total_lines': sum(route_line_counts.values()),
        'support_resolution': support_resolution,
        'stronger_scaffold_candidate': {
            'new_crate_name': 'os-node-runtime',
            'must_move_now': ['standalone_runtime.rs'] + route_modules,
            'must_resolve_or_inline': support_items,
            'keep_as_facade_in_os_node': ['src/lib.rs reexports', 'bin steelsearch', 'tests'],
        },
        'result': 'the_lowest_risk_stronger_scaffold_is_not_moving_standalone_runtime_rs_alone_but_moving_it_together_with_its_direct_route_registration_closure_behind_an_os_node_facade_crate',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
