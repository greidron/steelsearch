#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_handshake_success_path_does_not_locally_close_channel.py "
            "<TransportHandshaker.java> <NativeMessageHandler.java>",
            file=sys.stderr,
        )
        return 2

    handshaker = Path(sys.argv[1]).read_text()
    native_handler = Path(sys.argv[2]).read_text()

    source_handshake_success_path_returns_version_only = (
        "listener.onResponse(version);" in handshaker
        and "void handleResponse(HandshakeResponse response)" in handshaker
    )
    source_handshake_success_path_has_no_local_close = "listener.onResponse(version);" in handshaker and "channel.close" not in handshaker
    source_handshake_response_removes_pending_handler = "handler = handshaker.removeHandlerForHandshake(requestId);" in native_handler

    if (
        source_handshake_success_path_returns_version_only
        and source_handshake_success_path_has_no_local_close
        and source_handshake_response_removes_pending_handler
    ):
        result = (
            "java_handshake_success_path_does_not_locally_close_the_channel_and_normally_removes_the_pending_handler_"
            "so_handshake_channel_remote_eof_should_be_treated_as_peer_side_not_local_success_cleanup"
        )
    else:
        result = "handshake_success_local_close_exclusion_inconclusive"

    print(
        json.dumps(
            {
                "source_handshake_success_path_returns_version_only": source_handshake_success_path_returns_version_only,
                "source_handshake_success_path_has_no_local_close": source_handshake_success_path_has_no_local_close,
                "source_handshake_response_removes_pending_handler": source_handshake_response_removes_pending_handler,
                "result": result,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
