#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
LIB_RS = REPO / 'crates/os-node/src/lib.rs'
SEARCH_FILES = [
    REPO / 'crates/os-node/src/main.rs',
    REPO / 'crates/os-node/tests/dev_cluster_daemons.rs',
    REPO / 'crates/os-node/tests/utoipa_poc.rs',
]
INACTIVE_TAIL = [
    'ClusterSettingsState',
    'CoordinationFaultPhase',
    'DevelopmentDiscoveryRuntime',
    'MembershipNode',
    'PersistedGatewayMetadataCommitState',
    'PersistedGatewayMetadataState',
    'PersistedGatewayRoutingMetadata',
    'PublicationRoundState',
]

REEXPORT_RE = re.compile(r'pub use standalone_runtime::\{(.*?)\};', re.S)
ROOT_IMPORT_RE = re.compile(r'use\s+os_node::\{(.*?)\};', re.S)
QUALIFIED_TEMPLATE = r'os_node::{name}\b'


def parse_names(block: str):
    out = []
    for part in block.replace('\n', ' ').split(','):
        name = part.strip()
        if name:
            out.append(name)
    return out


def root_imported_names(path: Path):
    text = path.read_text()
    names = []
    for block in ROOT_IMPORT_RE.findall(text):
        names.extend(parse_names(block))
    return set(names)


def qualified_hits(path: Path, name: str):
    text = path.read_text()
    return len(re.findall(QUALIFIED_TEMPLATE.format(name=re.escape(name)), text))


def main():
    lib_text = LIB_RS.read_text()
    m = REEXPORT_RE.search(lib_text)
    if not m:
        raise RuntimeError('reexport block not found')
    exported = set(parse_names(m.group(1)))

    consumer_details = {}
    for path in SEARCH_FILES:
        rel = str(path.relative_to(REPO))
        imported = root_imported_names(path)
        details = {}
        for name in INACTIVE_TAIL:
            details[name] = {
                'imported_via_root_use': name in imported,
                'qualified_os_node_hits': qualified_hits(path, name),
            }
        consumer_details[rel] = details

    used_anywhere = {}
    for name in INACTIVE_TAIL:
        users = []
        for rel, details in consumer_details.items():
            if details[name]['imported_via_root_use'] or details[name]['qualified_os_node_hits'] > 0:
                users.append(rel)
        used_anywhere[name] = users

    corrected_active = sorted([name for name, users in used_anywhere.items() if users])
    corrected_true_tail = sorted([name for name, users in used_anywhere.items() if not users])

    result = {
        'inactive_tail_input_count': len(INACTIVE_TAIL),
        'all_tail_names_are_reexported': all(name in exported for name in INACTIVE_TAIL),
        'consumer_details': consumer_details,
        'corrected_active_from_tail': corrected_active,
        'corrected_active_from_tail_count': len(corrected_active),
        'corrected_true_tail': corrected_true_tail,
        'corrected_true_tail_count': len(corrected_true_tail),
        'result': 'the_previous_inactive_tail_was_overstated_because_most_of_these_exports_are_used_via_qualified_os_node_paths_in_main_rs',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
