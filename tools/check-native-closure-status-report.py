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
RELEASE_RECORD_ITEMS = (
    *READINESS_ATTACHMENT_ITEMS,
    "pit_e2e_coverage",
    "promotion_gate_suite",
)
CURRENT_EVIDENCE_GROUPS = (
    "non-native-inventory",
    "e2e-required-parity",
    "e2e-search-compat-parity",
    "e2e-broad-parity",
    "rest-api-coverage-current",
    "transport-action-coverage-current",
    "mixed-cluster-coverage-current",
    "materialization-priority-current",
    "production-security-current",
    "startup-bootstrap-current",
    "runtime-controls-current",
    "release-evidence-inventory-current",
    "release-readiness-tooling",
)
VALID_STATUSES = {
    "ready",
    "current-evidence-ready-final-cutover-pending",
    "final-cutover-missing",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument("--require-final-cutover", action="store_true")
    parser.add_argument("--require-clean-worktree", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(
        payload,
        require_final_cutover=args.require_final_cutover,
        require_clean_worktree=args.require_clean_worktree,
    )
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(
    payload: dict[str, Any],
    *,
    require_final_cutover: bool = False,
    require_clean_worktree: bool = False,
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
    if not isinstance(metadata.get("git_clean"), bool):
        errors.append("metadata.git_clean is missing or not a boolean")
    if not isinstance(metadata.get("git_status_short"), str):
        errors.append("metadata.git_status_short is missing or not a string")
    if require_clean_worktree and metadata.get("git_clean") is not True:
        errors.append("metadata.git_clean is not true")
    if require_clean_worktree and metadata.get("git_status_short") != "":
        errors.append("metadata.git_status_short is not empty")

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
    current_required_groups = tuple(current.get("required_groups") or ())
    if current_required_groups != CURRENT_EVIDENCE_GROUPS:
        errors.append("gates.current_evidence.required_groups mismatch")
    current_groups = current.get("groups")
    if not isinstance(current_groups, dict):
        errors.append("gates.current_evidence.groups is missing or not an object")
    else:
        for group in CURRENT_EVIDENCE_GROUPS:
            group_status = current_groups.get(group)
            if not isinstance(group_status, dict):
                errors.append(f"gates.current_evidence.groups.{group} is missing")
            elif group_status.get("ok") is not True:
                errors.append(f"gates.current_evidence.groups.{group}.ok is not true")
    transport_release_errors = transport_release_parity_errors(current)
    errors.extend(transport_release_errors)
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
    readiness_attachment_missing_items = final.get("readiness_attachment_missing_items")
    release_record_missing_items = final.get("release_record_missing_items")
    if not isinstance(release_record_missing_items, list):
        errors.append("final_cutover.release_record_missing_items is missing")
    if final.get("passed") is True and missing_items != []:
        errors.append("final_cutover passed but missing_items is not empty")
    if final.get("passed") is True and readiness_attachment_missing_items != []:
        errors.append(
            "final_cutover passed but readiness_attachment_missing_items is not empty"
        )
    if final.get("passed") is True and release_record_missing_items != []:
        errors.append(
            "final_cutover passed but release_record_missing_items is not empty"
        )
    if require_final_cutover and final.get("passed") is not True:
        errors.append("final_cutover.passed is not true")

    inventory = final.get("evidence_inventory")
    if not isinstance(inventory, dict):
        errors.append("final_cutover.evidence_inventory is missing or not an object")
    else:
        if not isinstance(inventory.get("returncode"), int):
            errors.append("final_cutover.evidence_inventory.returncode is missing or not an integer")
        inventory_summary = inventory.get("summary")
        if not isinstance(inventory_summary, dict):
            errors.append("final_cutover.evidence_inventory.summary is missing or not an object")
        else:
            startup_missing = inventory_summary.get("startup_missing_items")
            attachment_missing = inventory_summary.get("readiness_attachment_missing_items")
            release_record_missing = inventory_summary.get("release_record_missing_items")
            if not isinstance(startup_missing, list):
                errors.append("final_cutover.evidence_inventory.summary.startup_missing_items is missing")
            if not isinstance(attachment_missing, list):
                errors.append(
                    "final_cutover.evidence_inventory.summary.readiness_attachment_missing_items is missing"
                )
            if not isinstance(release_record_missing, list):
                errors.append(
                    "final_cutover.evidence_inventory.summary.release_record_missing_items is missing"
                )
            if final.get("passed") is True and inventory_summary.get("complete") is not True:
                errors.append("final_cutover passed but evidence inventory is not complete")
            if final.get("passed") is True and startup_missing != []:
                errors.append("final_cutover passed but evidence inventory startup_missing_items is not empty")
            if final.get("passed") is True and attachment_missing != []:
                errors.append(
                    "final_cutover passed but evidence inventory readiness_attachment_missing_items is not empty"
                )
            if final.get("passed") is True and release_record_missing != []:
                errors.append(
                    "final_cutover passed but evidence inventory release_record_missing_items is not empty"
                )

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
            "readiness_attachment_missing_items": readiness_attachment_missing_items,
            "release_record_missing_items": release_record_missing_items,
        },
    }


def gate(gates: dict[str, Any], name: str) -> dict[str, Any]:
    value = gates.get(name)
    return value if isinstance(value, dict) else {}


def transport_release_parity_errors(current: dict[str, Any]) -> list[str]:
    transport_result = None
    for result in current.get("results") or []:
        if isinstance(result, dict) and result.get("group") == "transport-action-coverage-current":
            transport_result = result
            break
    if transport_result is None:
        return ["gates.current_evidence.results transport-action-coverage-current is missing"]
    summary = transport_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results transport-action-coverage-current.summary is missing"]

    errors: list[str] = []
    if summary.get("release_parity_evidence_complete") is not True:
        errors.append(
            "gates.current_evidence.results transport release parity evidence is not complete"
        )
    if summary.get("release_parity_source_missing_action_count") != 0:
        errors.append(
            "gates.current_evidence.results transport release parity missing action count is not zero"
        )
    matched = summary.get("release_parity_source_matched_action_count")
    if not isinstance(matched, int) or matched <= 0:
        errors.append(
            "gates.current_evidence.results transport release parity matched action count is not positive"
        )
    return errors


if __name__ == "__main__":
    sys.exit(main())
