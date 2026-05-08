#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print(
            "usage: check_follower_check_empty_response_reference.py <report.json>",
            file=sys.stderr,
        )
        return 2

    report_path = Path(sys.argv[1])
    report = json.loads(report_path.read_text(encoding="utf-8"))

    captured = None
    for entry in report.get("steelsearch_transport_capture") or []:
        frame = entry.get("first_frame") or {}
        if frame.get("action_hint") == "internal:coordination/fault_detection/follower_check":
            response = entry.get("response_frame") or {}
            captured = {
                "request_id": frame.get("request_id"),
                "version_id": frame.get("version_id"),
                "body_prefix_hex": response.get("body_prefix_hex"),
                "message_length": response.get("message_length"),
            }
            break

    if captured is None:
        print(json.dumps({"report_path": str(report_path), "result": "missing_follower_check"}))
        return 1

    helper = subprocess.run(
        [
            "bash",
            "tools/dump_java_follower_check_empty_response.sh",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    reference_hex = helper.stdout.strip()
    reference_body_hex = reference_hex[12:] if len(reference_hex) >= 12 else reference_hex
    result = {
        "report_path": str(report_path),
        "captured": captured,
        "java_reference_hex": reference_hex,
        "java_reference_body_hex": reference_body_hex,
        "matches_reference": captured["body_prefix_hex"] == reference_body_hex,
    }
    print(json.dumps(result, indent=2))
    return 0 if result["matches_reference"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
