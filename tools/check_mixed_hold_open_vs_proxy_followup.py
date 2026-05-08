#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "usage: check_mixed_hold_open_vs_proxy_followup.py "
            "<mixed-followup-check.json> <proxy-followup-check.json>",
            file=sys.stderr,
        )
        return 2

    mixed = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    proxy = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))

    mixed_followup_failed = bool(mixed.get("completed_handshake_followup_failed", False))
    mixed_connection_reset = bool(mixed.get("connection_reset", False))
    proxy_followup_failed = bool(proxy.get("followup_failed", False))
    proxy_publish_state_count = int(proxy.get("publish_state_count", 0))

    result = {
        "mixed_followup_failed": mixed_followup_failed,
        "mixed_connection_reset": mixed_connection_reset,
        "proxy_followup_failed": proxy_followup_failed,
        "proxy_publish_state_count": proxy_publish_state_count,
    }
    if (not mixed_followup_failed) and (not mixed_connection_reset) and proxy_followup_failed and proxy_publish_state_count == 0:
        result["result"] = "mixed_tcp_handshake_hold_open_eliminates_followup_failure_but_proxy_path_still_stalls_before_publish_state"
    else:
        result["result"] = "mixed_vs_proxy_hold_open_gap_inconclusive"

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
