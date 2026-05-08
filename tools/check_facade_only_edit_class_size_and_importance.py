#!/usr/bin/env python3
import json
import re
from pathlib import Path

REPO = Path('/home/ubuntu/steelsearch')
OS_NODE = REPO / 'crates/os-node'
SRC = OS_NODE / 'src'
TESTS = OS_NODE / 'tests'

REEXPORT_RE = re.compile(r'pub use standalone_runtime::\{(.*?)\};', re.S)
ROOT_IMPORT_RE = re.compile(r'use\s+os_node::\{(.*?)\};', re.S)


def extract_names(block: str):
    names = []
    for part in block.replace('\n', ' ').split(','):
        name = part.strip()
        if name:
            names.append(name)
    return names


def main():
    lib_rs = (SRC / 'lib.rs').read_text()
    m = REEXPORT_RE.search(lib_rs)
    if not m:
        raise RuntimeError('standalone_runtime reexport block not found in lib.rs')
    reexported = extract_names(m.group(1))

    src_files = sorted(SRC.glob('*.rs'))
    src_line_counts = {p.name: sum(1 for _ in p.open()) for p in src_files}
    total_src_lines = sum(src_line_counts.values())
    lib_rs_lines = src_line_counts['lib.rs']
    helper_like_lines = total_src_lines - lib_rs_lines

    consumer_files = [SRC / 'main.rs'] + sorted(TESTS.glob('*.rs'))
    consumer_import_names = {}
    all_imported_names = []
    for path in consumer_files:
        text = path.read_text()
        names = []
        for block in ROOT_IMPORT_RE.findall(text):
            names.extend(extract_names(block))
        consumer_import_names[str(path.relative_to(REPO))] = names
        all_imported_names.extend(names)

    unique_imported_names = sorted(set(all_imported_names))
    matched_reexports = sorted(set(unique_imported_names) & set(reexported))
    unmatched_imports = sorted(set(unique_imported_names) - set(reexported))

    result = {
        'facade_file_count': 1,
        'facade_lines': lib_rs_lines,
        'helper_like_file_count': len(src_files) - 1,
        'helper_like_lines': helper_like_lines,
        'total_src_file_count': len(src_files),
        'total_src_lines': total_src_lines,
        'facade_line_share': round(lib_rs_lines / total_src_lines, 4),
        'standalone_runtime_reexport_count': len(reexported),
        'consumer_files': list(consumer_import_names.keys()),
        'consumer_root_import_name_counts': {k: len(v) for k, v in consumer_import_names.items()},
        'unique_root_import_count': len(unique_imported_names),
        'matched_reexport_count': len(matched_reexports),
        'unmatched_root_imports': unmatched_imports,
        'result': 'facade_only_edit_class_is_structurally_small_but_api_relevant_because_it_is_one_small_root_file_that_defines_the_root_import_surface_consumed_by_main_and_tests',
    }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
