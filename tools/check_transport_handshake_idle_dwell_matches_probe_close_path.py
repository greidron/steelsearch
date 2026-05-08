#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_transport_handshake_idle_dwell_matches_probe_close_path.py <probe_report.json> <HandshakingTransportAddressConnector.java>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    source_path = Path(sys.argv[2])
    report = json.loads(report_path.read_text())
    source = source_path.read_text()

    handshake_deltas = []
    for capture in report.get("steelsearch_transport_capture") or []:
        if (capture.get("first_frame") or {}).get("action_hint") != "internal:transport/handshake":
            continue
        sent = capture.get("response_frame_sent_at_ms")
        end = capture.get("connection_end_at_ms")
        if isinstance(sent, int) and isinstance(end, int):
            handshake_deltas.append(end - sent)

    has_probe_close_before_connect = (
        "handshake successful" in source
        and "IOUtils.closeWhileHandlingException(connection);" in source
        and "transportService.connectToNode(remoteNode" in source
        and source.index("IOUtils.closeWhileHandlingException(connection);")
        < source.index("transportService.connectToNode(remoteNode")
    )

    result = {
        "report_path": str(report_path),
        "source_path": str(source_path),
        "transport_handshake_count": len(handshake_deltas),
        "transport_handshake_gap_ms": {
            "min": min(handshake_deltas) if handshake_deltas else None,
            "median": sorted(handshake_deltas)[len(handshake_deltas) // 2] if handshake_deltas else None,
            "max": max(handshake_deltas) if handshake_deltas else None,
        },
        "source_has_probe_close_before_connect": has_probe_close_before_connect,
        "result": (
            "transport_handshake_idle_dwell_best_matches_the_probe_connection_close_then_connectToNode_source_path"
            if handshake_deltas and has_probe_close_before_connect
            else "transport_handshake_idle_dwell_not_matched_to_probe_close_path"
        ),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
