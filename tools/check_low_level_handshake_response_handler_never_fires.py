#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def count(text: str, needle: str) -> int:
    return text.count(needle)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_low_level_handshake_response_handler_never_fires.py <stdout.log>', file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    before_send = count(text, 'steelsearch_transport_handshaker_stage=before_send_request')
    after_send = count(text, 'steelsearch_transport_handshaker_stage=after_send_request')
    response_read = count(text, 'steelsearch_transport_handshaker_stage=response_read')
    handle_response = count(text, 'steelsearch_transport_handshaker_stage=handle_response')
    handle_exception = count(text, 'steelsearch_transport_handshaker_stage=handle_exception')
    handle_local_exception = count(text, 'steelsearch_transport_handshaker_stage=handle_local_exception')
    remove_handler = count(text, 'steelsearch_transport_handshaker_stage=remove_handler')
    handshake_timeout = count(text, 'handshake_timeout[1s]')
    channels_connected = count(text, 'steelsearch_tcp_open_stage=channels_connected_listener_onResponse')
    open_response = count(text, 'steelsearch_open_connection_stage=response')
    open_failure = count(text, 'steelsearch_open_connection_stage=failure')

    print(f'before_send_request={before_send}')
    print(f'after_send_request={after_send}')
    print(f'response_read={response_read}')
    print(f'handle_response={handle_response}')
    print(f'handle_exception={handle_exception}')
    print(f'handle_local_exception={handle_local_exception}')
    print(f'remove_handler={remove_handler}')
    print(f'handshake_timeout={handshake_timeout}')
    print(f'channels_connected_on_response={channels_connected}')
    print(f'open_response={open_response}')
    print(f'open_failure={open_failure}')

    if before_send > 0 and after_send > 0 and response_read == 0 and handle_response == 0 and handle_exception == 0 and handshake_timeout > 0:
        print('checker_result=low_level_tcp_handshake_times_out_before_any_response_handler_parse_or_callback')
    else:
        print('checker_result=inconclusive')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
