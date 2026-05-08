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
    standalone_text = STANDALONE.read_text()
    explicit_consumer_set = sorted(set(
        extract_root_imports(MAIN_RS)
        + extract_root_imports(TEST_RS)
        + extract_direct_root_type_uses(MAIN_RS)
        + extract_direct_root_type_uses(TEST_RS)
    ))

    standalone_exports = []
    for name in explicit_consumer_set:
        pub_pattern = rf'pub\s+(?:struct|enum|fn|type|trait|const)\s+{re.escape(name)}\b'
        if re.search(pub_pattern, standalone_text):
            standalone_exports.append(name)

    candidate = "pub use standalone_runtime::{\n    " + ",\n    ".join(standalone_exports) + ",\n};"
    result = {
        'standalone_export_count': len(standalone_exports),
        'standalone_exports': standalone_exports,
        'candidate_snippet': candidate,
        'result': 'explicit_export_list_candidate_generated_from_current_root_consumers',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
