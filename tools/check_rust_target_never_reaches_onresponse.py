#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_rust_target_never_reaches_onresponse.py <opensearch_stdout>', file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    rust_onresponse = text.count('steelsearch_publication_onResponse_entry discoveryNode={rust-replica-1}')
    self_onresponse = text.count('steelsearch_publication_onResponse_entry discoveryNode={java-primary-1}')
    rust_transport_failure = text.count('steelsearch_publication_response_class=transport_failure discoveryNode={rust-replica-1}')
    self_transport_failure = text.count('steelsearch_publication_response_class=transport_failure discoveryNode={java-primary-1}')

    print(f'rust_onresponse={rust_onresponse}')
    print(f'self_onresponse={self_onresponse}')
    print(f'rust_transport_failure={rust_transport_failure}')
    print(f'self_transport_failure={self_transport_failure}')

    if rust_onresponse == 0 and self_onresponse > 0 and rust_transport_failure > 0 and self_transport_failure == 0:
        print('result=rust_target_never_reaches_onresponse_and_disconnects_pre_callback_while_self_target_does_reach_onresponse')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
