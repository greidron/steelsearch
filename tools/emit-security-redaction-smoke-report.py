#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: emit-security-redaction-smoke-report.py <input-report> <output-report>")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    report = json.loads(input_path.read_text())

    redaction = {
        "artifact": "security-redaction-smoke",
        "profile": report["profile"],
        "failure_class": report.get("failure_class"),
        "expected_markers": report.get("expected_markers", []),
        "source_report": str(input_path),
        "status": report.get("status", "completed")
    }
    output_path.write_text(json.dumps(redaction, indent=2) + "\n")


if __name__ == "__main__":
    main()
