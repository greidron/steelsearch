#!/usr/bin/env python3
import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: emit-secure-durability-restart-report.py <input-report> <output-report>")

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    report = json.loads(input_path.read_text())
    transcript = report.get("stability_transcript", [])

    durability = {
        "artifact": "secure-durability-restart",
        "profile": report["profile"],
        "source_report": str(input_path),
        "stability_window": report.get("stability_window"),
        "poll_interval": report.get("poll_interval"),
        "step_count": len(report.get("steps", [])),
        "transcript_entry_count": len(transcript),
        "status": report.get("status", "completed")
    }
    output_path.write_text(json.dumps(durability, indent=2) + "\n")


if __name__ == "__main__":
    main()
