#!/usr/bin/env python3
"""Validate a native-closure status report artifact."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


STARTUP_MANIFEST_ITEMS = (
    "benchmark_coverage",
    "load_test_coverage",
    "chaos_test_coverage",
    "packaging_verified",
    "rolling_upgrade_coverage",
)
READINESS_ATTACHMENT_ITEMS = (*STARTUP_MANIFEST_ITEMS, "load_comparison")
VALID_STATUSES = {
    "ready",
    "current-evidence-ready-final-cutover-pending",
    "final-cutover-missing",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--require-final-cutover", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(payload, require_final_cutover=args.require_final_cutover)
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(
    payload: dict[str, Any],
    *,
    require_final_cutover: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    current = gate(gates, "current_evidence")
    peer = gate(gates, "runtime_peer_backpressure_current")
    final = gate(gates, "final_cutover")

    if not isinstance(metadata.get("generated_at_epoch_seconds"), int):
        errors.append("metadata.generated_at_epoch_seconds is missing or not an integer")
    if not isinstance(metadata.get("git_head"), str) or not metadata.get("git_head"):
        errors.append("metadata.git_head is missing or not a string")

    if summary.get("current_evidence_ready") is not True:
        errors.append("summary.current_evidence_ready is not true")
    if summary.get("runtime_peer_backpressure_ready") is not True:
        errors.append("summary.runtime_peer_backpressure_ready is not true")
    if summary.get("status") not in VALID_STATUSES:
        errors.append(f"summary.status is invalid: {summary.get('status')}")
    if require_final_cutover and summary.get("final_cutover_ready") is not True:
        errors.append("summary.final_cutover_ready is not true")
    if bool(summary.get("final_cutover_required")) != require_final_cutover:
        errors.append("summary.final_cutover_required does not match checker mode")

    if current.get("passed") is not True:
        errors.append("gates.current_evidence.passed is not true")
    if peer.get("passed") is not True:
        errors.append("gates.runtime_peer_backpressure_current.passed is not true")

    startup_items = tuple(final.get("startup_manifest_items") or ())
    attachment_items = tuple(final.get("readiness_attachment_items") or ())
    if startup_items != STARTUP_MANIFEST_ITEMS:
        errors.append("final_cutover.startup_manifest_items mismatch")
    if attachment_items != READINESS_ATTACHMENT_ITEMS:
        errors.append("final_cutover.readiness_attachment_items mismatch")
    if "load_comparison" in startup_items:
        errors.append("load_comparison must not be a startup manifest item")
    if "load_comparison" not in attachment_items:
        errors.append("load_comparison must be a readiness attachment item")

    missing_items = final.get("missing_items")
    if final.get("passed") is True and missing_items != []:
        errors.append("final_cutover passed but missing_items is not empty")
    if require_final_cutover and final.get("passed") is not True:
        errors.append("final_cutover.passed is not true")

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "status": summary.get("status"),
            "current_evidence_ready": summary.get("current_evidence_ready"),
            "runtime_peer_backpressure_ready": summary.get("runtime_peer_backpressure_ready"),
            "final_cutover_ready": summary.get("final_cutover_ready"),
            "missing_items": missing_items,
        },
    }


def gate(gates: dict[str, Any], name: str) -> dict[str, Any]:
    value = gates.get(name)
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    sys.exit(main())
