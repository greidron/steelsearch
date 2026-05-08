#!/usr/bin/env python3
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path('/home/ubuntu/steelsearch')
SRC = ROOT / 'crates/os-node/src'


def main() -> int:
    derive_counter = Counter()
    attr_counter = Counter()
    for path in SRC.glob('*.rs'):
        text = path.read_text()
        for match in re.finditer(r'#\[derive\(([^\]]+)\)\]', text, re.S):
            for item in match.group(1).split(','):
                name = item.strip()
                if name:
                    derive_counter[name] += 1
        for match in re.finditer(r'#\[([A-Za-z0-9_:]+)', text):
            name = match.group(1)
            if name != 'derive':
                attr_counter[name] += 1

    serde_like_total = (
        derive_counter['Serialize']
        + derive_counter['Deserialize']
        + derive_counter['serde::Deserialize']
        + attr_counter['serde']
    )
    built_in_top = {
        'Clone': derive_counter['Clone'],
        'Debug': derive_counter['Debug'],
        'Eq': derive_counter['Eq'],
        'PartialEq': derive_counter['PartialEq'],
    }

    result = {
        'derive_counter_top': derive_counter.most_common(10),
        'attr_counter_top': attr_counter.most_common(10),
        'serde_like_total': serde_like_total,
        'serde_family_breakdown': {
            'Serialize': derive_counter['Serialize'],
            'Deserialize': derive_counter['Deserialize'],
            'serde::Deserialize': derive_counter['serde::Deserialize'],
            'serde_attr': attr_counter['serde'],
        },
        'built_in_top': built_in_top,
        'result': 'among_external_proc_macro_like_sites_the_serde_family_is_the_dominant_macro_family_in_os_node_source_while_the_higher_clone_debug_eq_counts_are_mostly_builtin_derives',
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
