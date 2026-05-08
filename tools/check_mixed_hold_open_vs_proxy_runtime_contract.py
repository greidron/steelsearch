#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def load(path: str):
    return json.loads(Path(path).read_text())


def main() -> int:
    if len(sys.argv) != 3:
        print(json.dumps({"error": "usage: check_mixed_hold_open_vs_proxy_runtime_contract.py <mixed_hold_open_contract.json> <proxy_runtime_contract.json>"}))
        return 1

    mixed = load(sys.argv[1])
    proxy = load(sys.argv[2])

    mixed_hold_open = bool(
        mixed.get("tcp_handshake_branch_present")
        and mixed.get("tcp_handshake_reads_optional_follow_up")
        and mixed.get("tcp_handshake_followup_identity_hold_open")
        and mixed.get("tcp_handshake_no_followup_hold_open_15s")
    )
    proxy_transparent = bool(
        proxy.get("forwards_bytes_transparently")
        and proxy.get("propagates_eof_via_half_close")
        and proxy.get("opens_new_upstream_per_accept")
    )
    proxy_no_hold_open = not bool(proxy.get("has_application_level_followup_hold_open"))

    if mixed_hold_open and proxy_transparent and proxy_no_hold_open:
        result = "proxy_runtime_lacks_current_mixed_application_level_hold_open_acceptance_conditions"
    elif not mixed_hold_open:
        result = "mixed_hold_open_contract_missing"
    else:
        result = "proxy_runtime_contract_not_pure_transparent_pass_through"

    print(
        json.dumps(
            {
                "mixed_hold_open_contract_present": mixed_hold_open,
                "proxy_forwards_bytes_transparently": bool(proxy.get("forwards_bytes_transparently")),
                "proxy_propagates_eof_via_half_close": bool(proxy.get("propagates_eof_via_half_close")),
                "proxy_opens_new_upstream_per_accept": bool(proxy.get("opens_new_upstream_per_accept")),
                "proxy_has_application_level_followup_hold_open": bool(proxy.get("has_application_level_followup_hold_open")),
                "result": result,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
