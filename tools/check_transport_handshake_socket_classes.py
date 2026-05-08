#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: check_transport_handshake_socket_classes.py <report.json>"
        )

    report = json.loads(Path(sys.argv[1]).read_text())

    probe_upgrade = []
    direct_full_connect = []
    for entry in report["steelsearch_transport_capture"]:
        first_frame = entry.get("first_frame") or {}
        follow_up_frame = entry.get("follow_up_frame") or {}
        if first_frame.get("action_hint") == "internal:tcp/handshake" and follow_up_frame.get("action_hint") == "internal:transport/handshake":
            probe_upgrade.append(entry)
        elif first_frame.get("action_hint") == "internal:transport/handshake":
            direct_full_connect.append(entry)

    direct_full_connect_all_remote_eof = bool(direct_full_connect) and all(
        entry.get("connection_end") == "remote_eof" and entry.get("response_frame") is not None
        for entry in direct_full_connect
    )

    result = (
        "problematic_class_is_direct_full_connect_transport_handshake_socket_that_remote_eof_closes_after_identity_response"
        if direct_full_connect_all_remote_eof
        else "transport_handshake_socket_classes_not_fully_isolated"
    )

    print(
        json.dumps(
            {
                "probe_upgrade_socket_count": len(probe_upgrade),
                "direct_full_connect_transport_handshake_socket_count": len(direct_full_connect),
                "direct_full_connect_all_remote_eof": direct_full_connect_all_remote_eof,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
