#!/usr/bin/env python3
import sys
from pathlib import Path


def count(text: str, needle: str) -> int:
    return text.count(needle)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_tcptransport_timeout_override_not_injected.py <opensearch-stdout.log>')
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    override = count(text, 'steelsearch_tcp_open_stage=execute_handshake_timeout_override')
    before_send = count(text, 'steelsearch_transport_handshaker_stage=before_send_request')
    after_send = count(text, 'steelsearch_transport_handshaker_stage=after_send_request')
    open_failure = count(text, 'steelsearch_open_connection_stage=failure')
    timeout_5s = count(text, 'handshake_timeout[5s]')
    timeout_1s = count(text, 'handshake_timeout[1s]')

    print(f'override={override}')
    print(f'before_send_request={before_send}')
    print(f'after_send_request={after_send}')
    print(f'open_failure={open_failure}')
    print(f'timeout_5s={timeout_5s}')
    print(f'timeout_1s={timeout_1s}')

    if before_send > 0 and override == 0:
        print('checker_result=tcptransport_timeout_override_not_injected_even_though_other_server_overlays_are_active')
        return 0

    print('checker_result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
