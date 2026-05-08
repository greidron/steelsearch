#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_close_age_classes_split_probe_vs_named_rust.py <probe_report.json>', file=sys.stderr)
        return 2

    report_path = pathlib.Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding='utf-8'))
    stdout_path = pathlib.Path(report['artifacts']['opensearch_stdout'])
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')

    matches = re.findall(r'closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]', stdout_text)
    named_rust_band = 0
    address_only_zero = 0
    named_rust_other = 0
    address_only_other = 0
    for _, node, age_text in matches:
        age = int(age_text)
        is_named_rust = 'rust-replica-1' in node
        is_address_only = node.startswith('{127.0.0.1:')
        if is_named_rust and 700 <= age <= 850:
            named_rust_band += 1
        elif is_named_rust:
            named_rust_other += 1
        elif is_address_only and age == 0:
            address_only_zero += 1
        elif is_address_only:
            address_only_other += 1

    result = {
        'close_age_match_count': len(matches),
        'named_rust_band_700_850_count': named_rust_band,
        'named_rust_other_age_count': named_rust_other,
        'address_only_zero_count': address_only_zero,
        'address_only_other_age_count': address_only_other,
        'result': 'close_age_classes_split_into_address_only_probe_zero_ms_vs_named_rust_full_connection_700_850ms_band'
        if named_rust_band > 0 and address_only_zero > 0
        else 'close_age_classes_not_cleanly_split',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
