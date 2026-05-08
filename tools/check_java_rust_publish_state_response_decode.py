#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_java_rust_publish_state_response_decode.py <mixed-probe-report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))
    capture = report.get("steelsearch_transport_capture") or []
    publish_entries = [
        entry
        for entry in capture
        if ((entry.get("first_frame") or {}).get("action_hint") == "internal:cluster/coordination/publish_state")
    ]
    decoded = []
    for entry in publish_entries:
        body_hex = ((entry.get("response_frame") or {}).get("body_hex") or "")
        if not body_hex:
            continue
        output = subprocess.check_output(
            ["bash", "tools/parse_java_publish_with_join_response.sh", "--body-hex", body_hex],
            text=True,
            cwd=Path(__file__).resolve().parents[1],
        )
        decoded.append(json.loads(output))

    result = {
        "report_path": str(report_path),
        "publish_state_count": len(publish_entries),
        "decoded_count": len(decoded),
        "all_join_present": all(item.get("join_present") for item in decoded) if decoded else False,
        "decoded_terms": [item.get("term") for item in decoded],
        "decoded_versions": [item.get("version") for item in decoded],
    }
    if len(decoded) == len(publish_entries) and result["all_join_present"]:
        result["result"] = "publish_state_response_decodes_as_valid_publish_with_join_response"
    else:
        result["result"] = "publish_state_response_decode_inconclusive"
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
