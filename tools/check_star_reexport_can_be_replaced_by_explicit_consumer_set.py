#!/usr/bin/env python3
import json
import re
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
MAIN_RS = ROOT / 'crates/os-node/src/main.rs'
TEST_RS = ROOT / 'crates/os-node/tests/dev_cluster_daemons.rs'
STANDALONE = ROOT / 'crates/os-node/src/standalone_runtime.rs'


def extract_root_imports(path: Path) -> list[str]:
    text = path.read_text()
    match = re.search(r'use os_node::\{(.*?)\};', text, re.S)
    if not match:
        return []
    names = []
    for chunk in match.group(1).replace('\n', ' ').split(','):
        name = chunk.strip()
        if not name:
            continue
        name = name.split(' as ')[0].strip()
        if '::' in name:
            continue
        names.append(name)
    return names


def extract_direct_root_type_uses(path: Path) -> list[str]:
    text = path.read_text()
    return re.findall(r'\bos_node::([A-Z][A-Za-z0-9_]+)\b', text)


def main() -> int:
    repo_rs_files = list(ROOT.rglob('*.rs'))
    wildcard_import_hits = []
    for path in repo_rs_files:
        text = path.read_text()
        if 'use os_node::*;' in text:
            wildcard_import_hits.append(str(path))

    standalone_text = STANDALONE.read_text()
    main_imports = extract_root_imports(MAIN_RS)
    test_imports = extract_root_imports(TEST_RS)
    explicit_consumer_set = sorted(set(
        main_imports
        + test_imports
        + extract_direct_root_type_uses(MAIN_RS)
        + extract_direct_root_type_uses(TEST_RS)
    ))

    standalone_exported = []
    non_standalone = []
    for name in explicit_consumer_set:
        pub_pattern = rf'pub\s+(?:struct|enum|fn|type|trait|const)\s+{re.escape(name)}\b'
        if re.search(pub_pattern, standalone_text):
            standalone_exported.append(name)
        else:
            non_standalone.append(name)

    result = {
        'wildcard_import_hits': wildcard_import_hits,
        'explicit_consumer_set_size': len(explicit_consumer_set),
        'standalone_exported_count': len(standalone_exported),
        'non_standalone_count': len(non_standalone),
        'standalone_exported_names': standalone_exported,
        'non_standalone_names': non_standalone,
        'result': 'current_os_node_consumers_use_a_finite_explicit_root_import_set_with_no_wildcard_imports_so_the_standalone_runtime_star_reexport_can_in_principle_be_replaced_by_an_explicit_export_list',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
