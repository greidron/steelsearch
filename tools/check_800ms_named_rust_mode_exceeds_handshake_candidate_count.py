#!/usr/bin/env python3
import json
import pathlib
import re
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_800ms_named_rust_mode_exceeds_handshake_candidate_count.py <mixed_capture_report.json> <tcptransport_debug_report.json>', file=sys.stderr)
        return 2

    capture_report = json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    debug_report = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding='utf-8'))

    capture = capture_report['steelsearch_transport_capture']
    handshake_count = sum(
        1 for item in capture
        if (item.get('first_frame') or {}).get('action_hint') == 'internal:transport/handshake'
    )

    stdout_path = pathlib.Path(debug_report['artifacts']['opensearch_stdout'])
    stdout_text = stdout_path.read_text(encoding='utf-8', errors='replace')
    matches = re.findall(r'closed transport connection \[(\d+)\] to \[(.*?)\] with age \[(\d+)ms\]', stdout_text)
    named_rust_800 = sum(
        1 for _, node, age in matches
        if 'rust-replica-1' in node and 700 <= int(age) <= 850
    )

    result = {
        'transport_handshake_candidate_count': handshake_count,
        'named_rust_700_850_mode_count': named_rust_800,
        'result': 'named_rust_800ms_mode_cannot_be_pure_idle_handshake_subset_because_it_exceeds_handshake_candidate_count'
        if named_rust_800 > handshake_count
        else 'named_rust_800ms_mode_could_still_be_pure_idle_handshake_subset',
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
