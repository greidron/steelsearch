#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
LIB_RS = REPO / 'crates/os-node/src/lib.rs'
CONSUMERS = [
    REPO / 'crates/os-node/src/main.rs',
    REPO / 'crates/os-node/tests/dev_cluster_daemons.rs',
    REPO / 'crates/os-node/tests/utoipa_poc.rs',
]

REEXPORT_RE = re.compile(r'pub use standalone_runtime::\{(.*?)\};', re.S)
ROOT_IMPORT_RE = re.compile(r'use\s+os_node::\{(.*?)\};', re.S)


def parse_names(block: str):
    out = []
    for part in block.replace('\n', ' ').split(','):
        name = part.strip()
        if name:
            out.append(name)
    return out


def root_imports(path: Path):
    text = path.read_text()
    names = []
    for block in ROOT_IMPORT_RE.findall(text):
        names.extend(parse_names(block))
    return sorted(set(names))


def main():
    lib_text = LIB_RS.read_text()
    m = REEXPORT_RE.search(lib_text)
    if not m:
        raise RuntimeError('standalone_runtime reexport block not found')
    exported = sorted(parse_names(m.group(1)))

    consumer_map = {str(p.relative_to(REPO)): root_imports(p) for p in CONSUMERS}
    used_by = {name: [] for name in exported}
    for rel, names in consumer_map.items():
        for name in names:
            if name in used_by:
                used_by[name].append(rel)

    active = sorted([name for name, users in used_by.items() if users])
    inactive = sorted([name for name, users in used_by.items() if not users])
    main_path = 'crates/os-node/src/main.rs'
    test_path = 'crates/os-node/tests/dev_cluster_daemons.rs'
    main_only = sorted([name for name, users in used_by.items() if users == [main_path]])
    test_only = sorted([name for name, users in used_by.items() if users == [test_path]])
    shared = sorted([name for name, users in used_by.items() if len(users) > 1])

    result = {
        'standalone_runtime_export_count': len(exported),
        'active_root_consumer_subset_count': len(active),
        'inactive_export_tail_count': len(inactive),
        'active_root_consumer_subset': active,
        'inactive_export_tail': inactive,
        'main_only_count': len(main_only),
        'test_only_count': len(test_only),
        'shared_count': len(shared),
        'main_only_subset': main_only,
        'test_only_subset': test_only,
        'shared_subset': shared,
        'result': 'current_helper_lib_boundary_candidate_is_the_33_name_active_root_consumer_subset_while_8_exports_form_an_inactive_tail_that_can_be_deferred_or_reviewed_separately',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
