#!/usr/bin/env python3
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_full_opensearch_read_starvation_practical_stop.py <opensearch-stdout.log>", file=sys.stderr)
        return 2

    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")

    timeout_branch = text.count("steelsearch_tcp_open_stage=execute_handshake_failure_timeout_branch")
    grace_expire = text.count("steelsearch_tcp_open_stage=execute_handshake_failure_grace_expire")
    close_timeout = text.count("steelsearch_tcp_open_stage=close_and_fail_enter") and text.count("handshake_timeout[5s]")
    response_read = text.count("steelsearch_transport_handshaker_stage=response_read")
    handle_response = text.count("steelsearch_transport_handshaker_stage=handle_response")
    channel_read = text.count("steelsearch_netty4_message_channel_stage=channel_read")

    print(f"timeout_branch={timeout_branch}")
    print(f"grace_expire={grace_expire}")
    print(f"close_timeout={close_timeout}")
    print(f"response_read={response_read}")
    print(f"handle_response={handle_response}")
    print(f"channel_read={channel_read}")

    if timeout_branch > 0 and grace_expire > 0 and close_timeout > 0 and response_read == 0 and handle_response == 0:
        print("checker_result=full_opensearch_read_starvation_branch_is_at_practical_stop_point_and_backlog_pivot_is_reasonable")
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
