#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "usage: extract_proxy_followup_runtime_contract.py <capture_transport_proxy.py>"}))
        return 1

    text = Path(sys.argv[1]).read_text()
    result = {
        "captures_frames_for_observation": "capture.append(summarize_frame(" in text,
        "forwards_bytes_transparently": "dst.sendall(header + body)" in text,
        "propagates_eof_via_half_close": "dst.shutdown(socket.SHUT_WR)" in text,
        "opens_new_upstream_per_accept": "socket.create_connection((args.target_host, args.target_port))" in text,
        "has_application_level_followup_hold_open": "hold_transport_channel_open" in text or "Duration::from_secs(15)" in text,
        "parses_transport_actions_only_for_capture": "action_hint(body)" in text,
    }
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
