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


def main() -> int:
    standalone_text = STANDALONE.read_text()
    main_imports = extract_root_imports(MAIN_RS)
    test_imports = extract_root_imports(TEST_RS)
    all_imports = sorted(set(main_imports + test_imports))

    matched = []
    unmatched = []
    for name in all_imports:
        pub_pattern = rf'pub\s+(?:struct|enum|fn|type|trait|const)\s+{re.escape(name)}\b'
        if re.search(pub_pattern, standalone_text):
            matched.append(name)
        else:
            unmatched.append(name)

    result = {
        'main_root_import_count': len(main_imports),
        'test_root_import_count': len(test_imports),
        'unique_root_import_count': len(all_imports),
        'matched_to_standalone_runtime_count': len(matched),
        'matched_examples': matched[:20],
        'unmatched_examples': unmatched[:20],
        'result': 'standalone_runtime_star_reexport_is_an_actively_used_public_surface_for_the_os_node_binary_and_integration_tests'
        if matched
        else 'standalone_runtime_star_reexport_usage_is_not_confirmed',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
