#!/usr/bin/env python3
"""Report OpenSearch transport action inventory and current interop evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/rust-port/generated/source-transport-actions.tsv"
DEFAULT_PEER_REPORT = ROOT / "target/runtime-peer-backpressure-current.json"
HANDSHAKE_MATRIX = ROOT / "docs/rust-port/transport-handshake-version-skew-matrix.md"
MESSAGE_SEQUENCE = ROOT / "docs/rust-port/transport-message-sequence.md"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--peer-backpressure-report", default=str(DEFAULT_PEER_REPORT))
    parser.add_argument("--output")
    parser.add_argument("--require-peer-backpressure", action="store_true")
    args = parser.parse_args()

    actions = load_actions(Path(args.source))
    peer_report = load_optional_json(Path(args.peer_backpressure_report))
    errors: list[str] = []
    if args.require_peer_backpressure and not peer_report_passed(peer_report):
        errors.append("peer backpressure report is missing or not passed")

    protocol_evidence = {
        "handshake_version_skew_matrix": file_evidence(HANDSHAKE_MATRIX),
        "transport_message_sequence": file_evidence(MESSAGE_SEQUENCE),
        "peer_backpressure": {
            "path": str(Path(args.peer_backpressure_report)),
            "present": peer_report is not None,
            "passed": peer_report_passed(peer_report),
            "profile": (peer_report or {}).get("summary", {}).get("profile"),
            "scope": (peer_report or {}).get("profile", {}).get("scope"),
        },
    }

    status = "ok" if not errors else "failed"
    report = {
        "status": status,
        "errors": errors,
        "source": str(Path(args.source)),
        "summary": {
            "passed": not errors,
            "transport_action_count": len(actions),
            "implemented_action_count": count_status(actions, "implemented"),
            "planned_action_count": count_status(actions, "planned"),
            "stubbed_action_count": count_status(actions, "stubbed"),
            "out_of_scope_action_count": count_status(actions, "out-of-scope"),
            "action_coverage_claim": (
                "no OpenSearch ActionModule transport action is currently classified as implemented; "
                "current evidence covers frame/handshake/observe-only and query-phase backpressure surfaces"
            ),
            "peer_backpressure_passed": protocol_evidence["peer_backpressure"]["passed"],
        },
        "status_counts": status_counts(actions),
        "protocol_evidence": protocol_evidence,
        "planned_actions": actions,
    }
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if status == "ok" else 1


def load_actions(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return [
            {
                "status": row.get("status") or "",
                "action": row.get("action") or "",
                "transport_handler": row.get("transport_handler") or "",
                "source": row.get("source") or "",
                "line": row.get("line") or "",
            }
            for row in csv.DictReader(handle, delimiter="\t")
        ]


def load_optional_json(path_value: str) -> dict[str, Any] | None:
    path = Path(path_value)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def peer_report_passed(report: dict[str, Any] | None) -> bool:
    if not isinstance(report, dict):
        return False
    summary = report.get("summary")
    return isinstance(summary, dict) and summary.get("passed") is True


def file_evidence(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "present": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
    }


def count_status(actions: list[dict[str, str]], status: str) -> int:
    return sum(1 for action in actions if action["status"] == status)


def status_counts(actions: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        status = action["status"] or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


if __name__ == "__main__":
    sys.exit(main())
