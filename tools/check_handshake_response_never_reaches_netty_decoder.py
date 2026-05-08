#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_handshake_response_never_reaches_netty_decoder.py <stdout.log>', file=sys.stderr)
        return 2
    text = Path(sys.argv[1]).read_text(errors='replace')
    m = re.search(r'steelsearch_transport_handshaker_stage=before_send_request node=\{127\.0\.0\.1:(\d+)\}', text)
    port = m.group(1) if m else None
    channel_read_total = text.count('steelsearch_netty4_message_channel_stage=channel_read')
    handle_bytes_total = text.count('steelsearch_inbound_pipeline_stage=handle_bytes')
    before_send = text.count('steelsearch_transport_handshaker_stage=before_send_request')
    timeout = text.count('handshake_timeout[1s]')
    native_header = text.count('steelsearch_native_message_stage=handshake_response_header')
    if port is None:
        print('send_port=UNKNOWN')
        print(f'channel_read_total={channel_read_total}')
        print(f'handle_bytes_total={handle_bytes_total}')
        print('checker_result=inconclusive')
        return 0

    channel_read_for_port = len(re.findall(r'steelsearch_netty4_message_channel_stage=channel_read remote=/127\.0\.0\.1:' + re.escape(port) + r'\b', text))
    handle_bytes_for_port = len(re.findall(r'steelsearch_inbound_pipeline_stage=handle_bytes remote=/127\.0\.0\.1:' + re.escape(port) + r'\b', text))

    print(f'send_port={port}')
    print(f'before_send_request={before_send}')
    print(f'handshake_timeout={timeout}')
    print(f'channel_read_total={channel_read_total}')
    print(f'handle_bytes_total={handle_bytes_total}')
    print(f'channel_read_for_send_port={channel_read_for_port}')
    print(f'handle_bytes_for_send_port={handle_bytes_for_port}')
    print(f'native_handshake_response_header={native_header}')

    if before_send > 0 and timeout > 0 and channel_read_for_port == 0 and handle_bytes_for_port == 0 and native_header == 0:
        print('checker_result=handshake_response_never_reaches_netty4_message_channel_or_inbound_pipeline_for_send_port')
    else:
        print('checker_result=inconclusive')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
