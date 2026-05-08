#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit(
            "usage: check_transport_handshake_identity_equivalence.py <report.json>"
        )

    report = json.loads(Path(sys.argv[1]).read_text())

    probe_hexes = set()
    direct_hexes = set()

    def normalize(body_hex: str) -> str:
        return body_hex[26:] if len(body_hex) >= 26 else body_hex
    for entry in report["steelsearch_transport_capture"]:
        response = entry.get("response_frame") or {}
        body_hex = response.get("body_hex")
        if not body_hex:
            continue
        normalized = normalize(body_hex)
        first_frame = entry.get("first_frame") or {}
        follow_up_frame = entry.get("follow_up_frame") or {}
        if first_frame.get("action_hint") == "internal:tcp/handshake" and follow_up_frame.get("action_hint") == "internal:transport/handshake":
            probe_hexes.add(normalized)
        elif first_frame.get("action_hint") == "internal:transport/handshake":
            direct_hexes.add(normalized)

    equivalent = bool(probe_hexes) and bool(direct_hexes) and probe_hexes == direct_hexes
    result = (
        "probe_upgrade_and_direct_full_connect_transport_handshake_identity_responses_are_byte_identical"
        if equivalent
        else "transport_handshake_identity_equivalence_not_established"
    )

    print(
        json.dumps(
            {
                "probe_identity_variant_count": len(probe_hexes),
                "direct_identity_variant_count": len(direct_hexes),
                "responses_equivalent": equivalent,
                "result": result,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
