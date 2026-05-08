#!/usr/bin/env python3
import re
import sys
from pathlib import Path

PORT_PATTERNS = [
    (re.compile(r'OPENSEARCH_HTTP_PORT=\d+'), 'OPENSEARCH_HTTP_PORT=<PORT>'),
    (re.compile(r'OPENSEARCH_TRANSPORT_PORT=\d+'), 'OPENSEARCH_TRANSPORT_PORT=<PORT>'),
    (re.compile(r'STEELSEARCH_HTTP_PORT=\d+'), 'STEELSEARCH_HTTP_PORT=<PORT>'),
    (re.compile(r'STEELSEARCH_TRANSPORT_PORT=\d+'), 'STEELSEARCH_TRANSPORT_PORT=<PORT>'),
]


def normalize(text: str) -> str:
    for pattern, replacement in PORT_PATTERNS:
        text = pattern.sub(replacement, text)
    return text.strip()


def read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8').strip()


def main() -> int:
    if len(sys.argv) != 5:
        print('usage: check_rust_primary_java_replica_start_command_delta.py <formed-os-start> <formed-ss-start> <failed-os-start> <failed-ss-start>', file=sys.stderr)
        return 2

    formed_os = read(sys.argv[1])
    formed_ss = read(sys.argv[2])
    failed_os = read(sys.argv[3])
    failed_ss = read(sys.argv[4])

    formed_os_norm = normalize(formed_os)
    formed_ss_norm = normalize(formed_ss)
    failed_os_norm = normalize(failed_os)
    failed_ss_norm = normalize(failed_ss)

    print(f'formed_os_normalized={formed_os_norm}')
    print(f'failed_os_normalized={failed_os_norm}')
    print(f'formed_ss_normalized={formed_ss_norm}')
    print(f'failed_ss_normalized={failed_ss_norm}')
    print(f'opensearch_start_same_shape={formed_os_norm == failed_os_norm}')
    print(f'steelsearch_start_same_shape={formed_ss_norm == failed_ss_norm}')

    if formed_os_norm == failed_os_norm and formed_ss_norm == failed_ss_norm:
        print('result=visible_start_command_shape_same_between_formed_and_failed_runs')
        return 0

    print('result=visible_start_command_delta_present')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
