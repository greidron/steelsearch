#!/usr/bin/env python3
import json
import pathlib
import re
import statistics
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_named_rust_close_age_modes.py <probe_report.json>', file=sys.stderr)
        return 2

    report_path = pathlib.Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding='utf-8'))
    stdout_path = pathlib.Path(report['artifacts']['opensearch_stdout'])
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')

    matches = re.findall(r'closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]', stdout_text)
    rust_ages = [int(age) for _, node, age in matches if 'rust-replica-1' in node]

    mode_600 = [age for age in rust_ages if 600 <= age <= 604]
    mode_800 = [age for age in rust_ages if 700 <= age <= 850]
    outlier_2004 = [age for age in rust_ages if age >= 2000]
    other = [age for age in rust_ages if age not in mode_600 and age not in mode_800 and age not in outlier_2004]

    result = {
        'named_rust_close_age_count': len(rust_ages),
        'named_rust_close_age_ms': {
            'min': min(rust_ages),
            'median': statistics.median(rust_ages),
            'max': max(rust_ages),
        },
        'mode_600_604_count': len(mode_600),
        'mode_700_850_count': len(mode_800),
        'mode_2000_plus_count': len(outlier_2004),
        'other_count': len(other),
        'result': 'named_rust_close_ages_split_into_dominant_700_850_mode_secondary_600_604_mode_and_single_2004_outlier'
        if len(mode_800) > 0 and len(mode_600) > 0 and len(outlier_2004) > 0 and len(other) == 0
        else 'named_rust_close_age_modes_not_cleanly_split',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
