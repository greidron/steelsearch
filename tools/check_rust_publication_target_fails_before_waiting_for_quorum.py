#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('usage: check_rust_publication_target_fails_before_waiting_for_quorum.py <opensearch_stdout>', file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(errors='replace')
    rust_waiting = text.count('steelsearch_publication_target_state=waiting_for_quorum discoveryNode={rust-replica-1}')
    self_waiting = text.count('steelsearch_publication_target_state=waiting_for_quorum discoveryNode={java-primary-1}')
    rust_failed = text.count('steelsearch_publication_target_state=failed discoveryNode={rust-replica-1}')
    self_failed = text.count('steelsearch_publication_target_state=failed discoveryNode={java-primary-1}')
    rust_sent_publish_disconnect = text.count('discoveryNode={rust-replica-1}') and text.count('previousState=SENT_PUBLISH_REQUEST causeClass=org.opensearch.transport.NodeDisconnectedException')
    accepted = text.count('steelsearch_handlePublishResponse_gate=accepted')

    print(f'rust_waiting_for_quorum={rust_waiting}')
    print(f'self_waiting_for_quorum={self_waiting}')
    print(f'rust_failed={rust_failed}')
    print(f'self_failed={self_failed}')
    print(f'accepted={accepted}')
    print(f'rust_sent_publish_disconnect={rust_sent_publish_disconnect}')

    if rust_waiting == 0 and self_waiting > 0 and rust_failed > 0 and self_failed > 0 and accepted == self_waiting and rust_sent_publish_disconnect > 0:
        print('result=rust_publication_target_never_reaches_waiting_for_quorum_and_instead_fails_from_sent_publish_request_via_disconnect')
        return 0

    print('result=inconclusive')
    return 1


if __name__ == '__main__':
    raise SystemExit(main())
