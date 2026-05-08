#!/usr/bin/env python3
import json
import re
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: extract_tcp_handshake_hold_open_contract.py <main.rs>",
            file=sys.stderr,
        )
        return 1

    source = Path(sys.argv[1]).read_text(encoding="utf-8")
    anchor = "if is_request && is_handshake {"
    start = source.find(anchor)
    snippet = source[start : start + 4200] if start != -1 else ""
    hold_open_calls = len(re.findall(r"hold_transport_channel_open\(", snippet))
    result = {
        "tcp_handshake_branch_present": start != -1,
        "tcp_handshake_reads_optional_follow_up": "read_transport_seed_frame(&mut stream)?" in snippet,
        "tcp_handshake_followup_identity_hold_open": hold_open_calls >= 2,
        "tcp_handshake_no_followup_hold_open_15s": hold_open_calls >= 2 and "Duration::from_secs(15)" in snippet,
    }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
