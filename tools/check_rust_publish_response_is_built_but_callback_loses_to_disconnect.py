#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path


def series(text: str, key: str) -> list[int]:
    return [int(m.group(1)) for m in re.finditer(rf'{re.escape(key)}(\d+)', text)]


def main() -> int:
    if len(sys.argv) != 3:
        print('usage: check_rust_publish_response_is_built_but_callback_loses_to_disconnect.py <steelsearch_stderr> <opensearch_stdout>', file=sys.stderr)
        return 2

    stderr_text = Path(sys.argv[1]).read_text(errors='replace')
    stdout_text = Path(sys.argv[2]).read_text(errors='replace')

    decode = series(stderr_text, 'steelsearch_publish_state_decode_ms=')
    build = series(stderr_text, 'steelsearch_publish_state_build_ms=')
    total = series(stderr_text, 'steelsearch_publish_state_total_before_write_ms=')
    rust_onresponse = stdout_text.count('steelsearch_publication_onResponse_entry discoveryNode={rust-replica-1}')
    rust_transport_failure = stdout_text.count('steelsearch_publication_response_class=transport_failure discoveryNode={rust-replica-1}')
    rust_failed_sent_publish = stdout_text.count('previousState=SENT_PUBLISH_REQUEST causeClass=org.opensearch.transport.NodeDisconnectedException')

    print(f'decode_count={len(decode)} decode_tail={decode[-3:] if decode else []}')
    print(f'build_count={len(build)} build_tail={build[-3:] if build else []}')
    print(f'total_count={len(total)} total_tail={total[-3:] if total else []}')
    print(f'rust_onresponse={rust_onresponse}')
    print(f'rust_transport_failure={rust_transport_failure}')
    print(f'rust_failed_sent_publish={rust_failed_sent_publish}')

    if len(total) > 0 and max(total) > 0 and rust_onresponse == 0 and rust_transport_failure > 0 and rust_failed_sent_publish == rust_transport_failure:
        print('result=rust_publish_response_build_path_executes_but_java_callback_loses_to_pre_onresponse_disconnect')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
