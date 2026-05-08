#!/usr/bin/env python3
import json
import pathlib
import re
import statistics
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_tcptransport_close_age_trace_matches_idle_handshake_band.py <probe_report.json>', file=sys.stderr)
        return 2

    report_path = pathlib.Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding='utf-8'))
    stdout_path = pathlib.Path(report['artifacts']['opensearch_stdout'])
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')

    close_matches = re.findall(r'closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]', stdout_text)
    rust_ages = []
    zeroish_ages = []
    for _, node_text, age_text in close_matches:
        age = int(age_text)
        if 'rust-replica-1' in node_text:
            rust_ages.append(age)
        else:
            zeroish_ages.append(age)

    rust_band = [age for age in rust_ages if 700 <= age <= 850]
    result = {
        'close_age_match_count': len(close_matches),
        'rust_close_age_count': len(rust_ages),
        'rust_close_age_band_700_850_count': len(rust_band),
        'rust_close_age_ms': {
            'min': min(rust_ages) if rust_ages else None,
            'median': statistics.median(rust_ages) if rust_ages else None,
            'max': max(rust_ages) if rust_ages else None,
        },
        'non_rust_close_age_zero_count': sum(1 for age in zeroish_ages if age == 0),
        'result': 'java_tcptransport_debug_trace_directly_observes_peer_side_close_age_in_same_band_as_idle_handshake_sibling'
        if rust_ages and rust_band and sum(1 for age in zeroish_ages if age == 0) > 0
        else 'tcptransport_debug_trace_does_not_yet_directly_observe_expected_close_age_pattern',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
