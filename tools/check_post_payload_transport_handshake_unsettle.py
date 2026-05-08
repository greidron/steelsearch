#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            "usage: check_post_payload_transport_handshake_unsettle.py <ClusterConnectionManager.java> <report.json>"
        )

    connection_manager = Path(sys.argv[1]).read_text()
    report = json.loads(Path(sys.argv[2]).read_text())

    source_close_listener_unregisters = (
        "conn.addCloseListener" in connection_manager and "connectedNodes.remove(node, finalConnection);" in connection_manager
    )

    entries = [
        entry
        for entry in report["steelsearch_transport_capture"]
        if (entry.get("first_frame") or {}).get("action_hint") == "internal:transport/handshake"
    ]

    all_identity_response_then_remote_eof = bool(entries) and all(
        entry.get("response_frame") is not None and entry.get("connection_end") == "remote_eof"
        for entry in entries
    )

    result = (
        "post_payload_corrected_transport_handshake_channels_still_close_immediately_so_any_provisional_connectedNodes_registration_would_be_unsettled"
        if source_close_listener_unregisters and all_identity_response_then_remote_eof
        else "post_payload_transport_handshake_unsettle_gap_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "source_close_listener_unregisters": source_close_listener_unregisters,
                "transport_handshake_count": len(entries),
                "all_identity_response_then_remote_eof": all_identity_response_then_remote_eof,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
