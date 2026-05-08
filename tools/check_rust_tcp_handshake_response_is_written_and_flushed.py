#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def count(text: str, needle: str) -> int:
    return text.count(needle)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_rust_tcp_handshake_response_is_written_and_flushed.py <steelsearch-stderr.log>', file=sys.stderr)
        return 2
    text = Path(sys.argv[1]).read_text(errors='replace')
    before = count(text, 'steelsearch_tcp_handshake_response_stage=before_write')
    after_write = count(text, 'steelsearch_tcp_handshake_response_stage=after_write')
    after_flush = count(text, 'steelsearch_tcp_handshake_response_stage=after_flush')
    no_follow_up = count(text, 'steelsearch_tcp_handshake_response_stage=no_follow_up_within_400ms')
    follow_up = count(text, 'steelsearch_tcp_handshake_response_stage=follow_up_received')

    print(f'before_write={before}')
    print(f'after_write={after_write}')
    print(f'after_flush={after_flush}')
    print(f'no_follow_up_within_400ms={no_follow_up}')
    print(f'follow_up_received={follow_up}')

    if before > 0 and after_write == before and after_flush == before and no_follow_up > 0 and follow_up == 0:
        print('checker_result=rust_low_level_tcp_handshake_response_is_written_and_flushed_but_no_followup_arrives')
    else:
        print('checker_result=inconclusive')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
