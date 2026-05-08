#!/usr/bin/env python3
import json
import sys
from collections import Counter
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_java_java_proxy_followup_acceptance.py "
            "<proxy-capture.json> <primary-stdout.log>",
            file=sys.stderr,
        )
        return 2

    capture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    stdout_text = Path(sys.argv[2]).read_text(encoding="utf-8", errors="replace")
    counts = Counter(entry.get("action_hint") for entry in capture if entry.get("action_hint"))

    tcp_handshake_count = counts.get("internal:tcp/handshake", 0)
    transport_handshake_count = counts.get("internal:transport/handshake", 0)
    publish_state_count = counts.get("internal:cluster/coordination/publish_state", 0)
    followup_failed = "completed handshake with" in stdout_text and "followup connection failed" in stdout_text
    connection_reset = "connection reset" in stdout_text.lower() or "general node connection failure" in stdout_text.lower()

    result = {
        "tcp_handshake_count": tcp_handshake_count,
        "transport_handshake_count": transport_handshake_count,
        "publish_state_count": publish_state_count,
        "followup_failed": followup_failed,
        "connection_reset": connection_reset,
    }
    if tcp_handshake_count > 0 and transport_handshake_count > 0 and publish_state_count == 0 and followup_failed:
        result["result"] = "proxy_reference_fails_followup_acceptance_before_publish_state"
    else:
        result["result"] = "proxy_followup_acceptance_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
