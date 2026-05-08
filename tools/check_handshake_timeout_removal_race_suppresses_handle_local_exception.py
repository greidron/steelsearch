#!/usr/bin/env python3
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_handshake_timeout_removal_race_suppresses_handle_local_exception.py <opensearch-stdout.log>",
            file=sys.stderr,
        )
        return 2

    stdout = Path(sys.argv[1]).read_text(errors="replace")

    counts = {
        "before_send_request": stdout.count("steelsearch_transport_handshaker_stage=before_send_request"),
        "after_send_request": stdout.count("steelsearch_transport_handshaker_stage=after_send_request"),
        "response_read": stdout.count("steelsearch_transport_handshaker_stage=response_read"),
        "handle_response": stdout.count("steelsearch_transport_handshaker_stage=handle_response"),
        "handle_exception": stdout.count("steelsearch_transport_handshaker_stage=handle_exception"),
        "handle_local_exception": stdout.count("steelsearch_transport_handshaker_stage=handle_local_exception"),
        "remove_handler": stdout.count("steelsearch_transport_handshaker_stage=remove_handler"),
        "handshake_timeout": stdout.count("handshake_timeout[1s]"),
    }

    close_stack_mentions_handle_local_exception = len(
        re.findall(
            r"steelsearch_netty4_tcpchannel_stage=close_invoked .*?"
            r"TransportHandshaker\$HandshakeResponseHandler#handleLocalException:184",
            stdout,
        )
    )

    for key, value in counts.items():
        print(f"{key}={value}")
    print(f"close_stack_mentions_handleLocalException={close_stack_mentions_handle_local_exception}")

    if (
        counts["before_send_request"] > 0
        and counts["after_send_request"] == counts["before_send_request"]
        and counts["response_read"] == 0
        and counts["handle_response"] == 0
        and counts["handle_exception"] == 0
        and counts["handle_local_exception"] == 0
        and counts["handshake_timeout"] > 0
        and counts["remove_handler"] >= counts["handshake_timeout"] * 2
        and close_stack_mentions_handle_local_exception > 0
    ):
        print(
            "checker_result="
            "handshake_timeout_removes_handler_first_and_later_close_callback_enters_"
            "handleLocalException_after_removal"
        )
        return 0

    print("checker_result=inconclusive_or_different_ordering")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
