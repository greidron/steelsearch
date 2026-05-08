#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def count(text: str, needle: str) -> int:
    return text.count(needle)


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_handshake_response_never_reaches_native_message_handler.py <stdout.log>', file=sys.stderr)
        return 2
    text = Path(sys.argv[1]).read_text(errors='replace')
    before_send = count(text, 'steelsearch_transport_handshaker_stage=before_send_request')
    after_send = count(text, 'steelsearch_transport_handshaker_stage=after_send_request')
    native_header = count(text, 'steelsearch_native_message_stage=handshake_response_header')
    native_lookup = count(text, 'steelsearch_native_message_stage=handshake_response_handler_lookup')
    native_dispatch = count(text, 'steelsearch_native_message_stage=handshake_response_dispatch')
    native_dispatch_empty = count(text, 'steelsearch_native_message_stage=handshake_response_dispatch_empty')
    response_read = count(text, 'steelsearch_transport_handshaker_stage=response_read')
    handle_response = count(text, 'steelsearch_transport_handshaker_stage=handle_response')
    remove_handler = count(text, 'steelsearch_transport_handshaker_stage=remove_handler')
    timeout = count(text, 'handshake_timeout[1s]')

    print(f'before_send_request={before_send}')
    print(f'after_send_request={after_send}')
    print(f'native_handshake_response_header={native_header}')
    print(f'native_handshake_response_handler_lookup={native_lookup}')
    print(f'native_handshake_response_dispatch={native_dispatch}')
    print(f'native_handshake_response_dispatch_empty={native_dispatch_empty}')
    print(f'response_read={response_read}')
    print(f'handle_response={handle_response}')
    print(f'remove_handler={remove_handler}')
    print(f'handshake_timeout={timeout}')

    if before_send > 0 and after_send > 0 and native_header == 0 and response_read == 0 and timeout > 0:
        print('checker_result=handshake_response_never_reaches_native_message_handler_or_response_parser')
    else:
        print('checker_result=inconclusive')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
