#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 4:
        print(
            json.dumps(
                {
                    "error": "usage: check_probe_close_contract_vs_mixed_proxy.py <hold_open_contract.json> <mixed_followup.json> <proxy_followup.json>"
                }
            )
        )
        return 1

    hold_open = load(sys.argv[1])
    mixed = load(sys.argv[2])
    proxy = load(sys.argv[3])

    hold_open_enabled = bool(
        hold_open.get("tcp_handshake_branch_present")
        and hold_open.get("tcp_handshake_reads_optional_follow_up")
        and hold_open.get("tcp_handshake_followup_identity_hold_open")
        and hold_open.get("tcp_handshake_no_followup_hold_open_15s")
    )
    mixed_followup_cleared = not bool(mixed.get("completed_handshake_followup_failed")) and not bool(
        mixed.get("connection_reset")
    )
    proxy_still_stalled = bool(proxy.get("followup_failed")) and int(proxy.get("publish_state_count", 0)) == 0

    if hold_open_enabled and mixed_followup_cleared and proxy_still_stalled:
        result = "current_mixed_hold_open_contract_present_but_java_java_proxy_still_stalls_pre_publish"
    elif not hold_open_enabled:
        result = "hold_open_contract_not_detected"
    elif not mixed_followup_cleared:
        result = "mixed_followup_not_cleared"
    else:
        result = "proxy_gap_not_reproduced"

    print(
        json.dumps(
            {
                "hold_open_contract_present": hold_open_enabled,
                "mixed_followup_failed": bool(mixed.get("completed_handshake_followup_failed")),
                "mixed_connection_reset": bool(mixed.get("connection_reset")),
                "proxy_followup_failed": bool(proxy.get("followup_failed")),
                "proxy_publish_state_count": int(proxy.get("publish_state_count", 0)),
                "result": result,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
