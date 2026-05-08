#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: check_high_level_handshake_timeout_without_observed_followup.py "
            "<TransportHandshaker.java> <opensearch-stdout.log> <transport-seed-capture.json>",
            file=sys.stderr,
        )
        return 2

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    stdout = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
    capture = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8"))

    source_sends_handshake = "handshakeRequestSender.sendRequest" in source
    source_schedules_timeout = 'handshake_timeout[' in source and "threadPool.schedule(" in source

    channels_connected_on_response = stdout.count(
        "steelsearch_tcp_open_stage=channels_connected_listener_onResponse"
    )
    open_failure = stdout.count("steelsearch_open_connection_stage=failure")
    handshake_timeout = stdout.count("handshake_timeout[1s]")

    observed_transport_handshake_follow_up = 0
    for item in capture:
        follow = item.get("follow_up_frame") or {}
        post_follow = item.get("post_follow_up_frame") or {}
        if follow.get("action_hint") == "internal:transport/handshake":
            observed_transport_handshake_follow_up += 1
        if post_follow.get("action_hint") == "internal:transport/handshake":
            observed_transport_handshake_follow_up += 1

    print(f"source_sends_handshake={source_sends_handshake}")
    print(f"source_schedules_timeout={source_schedules_timeout}")
    print(f"channels_connected_on_response={channels_connected_on_response}")
    print(f"open_failure={open_failure}")
    print(f"handshake_timeout={handshake_timeout}")
    print(f"observed_transport_handshake_follow_up={observed_transport_handshake_follow_up}")

    if (
        source_sends_handshake
        and source_schedules_timeout
        and channels_connected_on_response > 0
        and open_failure > 0
        and handshake_timeout > 0
        and observed_transport_handshake_follow_up == 0
    ):
        print(
            "checker_result=java_high_level_handshake_times_out_without_any_observed_internal_transport_handshake_followup_at_rust"
        )
        return 0

    print("checker_result=inconclusive")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
