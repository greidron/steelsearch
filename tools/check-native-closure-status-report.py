#!/usr/bin/env python3
"""Validate a native-closure status report artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
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
    parser.add_argument("--require-current-head", action="store_true")
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(
        payload,
        require_final_cutover=args.require_final_cutover,
        require_clean_worktree=args.require_clean_worktree,
        expected_git_head=(current_git_head() if args.require_current_head else None),
    )
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(
    payload: dict[str, Any],
    *,
    require_final_cutover: bool = False,
    require_clean_worktree: bool = False,
    expected_git_head: str | None = None,
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
    if expected_git_head is not None and metadata.get("git_head") != expected_git_head:
        errors.append(
            "metadata.git_head does not match current HEAD "
            f"({metadata.get('git_head')} != {expected_git_head})"
        )
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
    rest_coverage_errors = rest_api_coverage_explanation_errors(current)
    errors.extend(rest_coverage_errors)
    pit_coverage_errors = pit_e2e_coverage_errors(current)
    errors.extend(pit_coverage_errors)
    broad_coverage_errors = broad_e2e_section_errors(current)
    errors.extend(broad_coverage_errors)
    mixed_cluster_errors = mixed_cluster_coverage_errors(current)
    errors.extend(mixed_cluster_errors)
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


def current_git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=Path(__file__).resolve().parents[1],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    )
    return completed.stdout.strip()


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
    release_scope_counts = summary.get("release_evidence_scope_counts")
    if not isinstance(release_scope_counts, dict):
        errors.append(
            "gates.current_evidence.results transport release evidence scope counts are missing"
        )
    else:
        runtime_action_parity_count = release_scope_counts.get("runtime_action_parity")
        if not isinstance(runtime_action_parity_count, int) or runtime_action_parity_count != matched:
            errors.append(
                "gates.current_evidence.results transport release runtime-action scope count "
                "does not match matched action count"
            )
    claim_boundary = summary.get("transport_execution_claim_boundary")
    if not isinstance(claim_boundary, str) or "does not promote generic transport action execution" not in claim_boundary:
        errors.append(
            "gates.current_evidence.results transport execution claim boundary is missing"
        )
    return errors


def rest_api_coverage_explanation_errors(current: dict[str, Any]) -> list[str]:
    rest_result = None
    for result in current.get("results") or []:
        if isinstance(result, dict) and result.get("group") == "rest-api-coverage-current":
            rest_result = result
            break
    if rest_result is None:
        return ["gates.current_evidence.results rest-api-coverage-current is missing"]
    summary = rest_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results rest-api-coverage-current.summary is missing"]

    errors: list[str] = []
    coverage_count = summary.get("live_required_matched_source_route_count")
    in_scope_count = summary.get("in_scope_source_route_count")
    coverage_ratio = summary.get("live_required_matched_source_route_ratio")
    if not isinstance(coverage_count, int) or coverage_count <= 0:
        errors.append(
            "gates.current_evidence.results REST live required matched source route count is not positive"
        )
    if not isinstance(in_scope_count, int) or in_scope_count <= 0:
        errors.append(
            "gates.current_evidence.results REST in-scope source route count is not positive"
        )
    if coverage_count != in_scope_count:
        errors.append(
            "gates.current_evidence.results REST live required matched source route count "
            "does not equal in-scope source route count"
        )
    if coverage_ratio != 1.0:
        errors.append(
            "gates.current_evidence.results REST live required matched source route ratio is not 1.0"
        )

    steelsearch_only_summary = summary.get(
        "unified_required_suite_steelsearch_only_summary"
    )
    if not isinstance(steelsearch_only_summary, dict):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only summary is missing"
        )
        return errors
    if steelsearch_only_summary.get("raw_delta") != 0:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only raw delta is not zero"
        )
    if steelsearch_only_summary.get("effective_unexplained_delta") != 0:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only unexplained effective delta is not zero"
        )
    raw_total = steelsearch_only_summary.get("raw_total")
    required_breakdown = summary.get(
        "unified_required_suite_steelsearch_only_breakdown"
    )
    if not isinstance(required_breakdown, list):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only required breakdown is missing"
        )
    elif isinstance(raw_total, int) and raw_total > 0 and not required_breakdown:
        errors.append(
            "gates.current_evidence.results REST steelsearch-only required breakdown is empty"
        )
    if not isinstance(
        summary.get("unified_non_required_suite_steelsearch_only_breakdown"), list
    ):
        errors.append(
            "gates.current_evidence.results REST steelsearch-only non-required breakdown is missing"
        )
    return errors


def pit_e2e_coverage_errors(current: dict[str, Any]) -> list[str]:
    pit_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "e2e-search-compat-parity"
            and result.get("name")
            == "pit_e2e_reports_have_required_opensearch_compared_cases_without_skips"
        ):
            pit_result = result
            break
    if pit_result is None:
        return ["gates.current_evidence.results PIT E2E coverage result is missing"]
    summary = pit_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results PIT E2E coverage summary is missing"]

    errors: list[str] = []
    required_count = summary.get("required_pit_case_count")
    compared_count = summary.get("required_pit_compared_case_count")
    if not isinstance(required_count, int) or required_count <= 0:
        errors.append(
            "gates.current_evidence.results PIT required case count is not positive"
        )
    if not isinstance(compared_count, int) or compared_count <= 0:
        errors.append(
            "gates.current_evidence.results PIT compared case count is not positive"
        )
    if required_count != compared_count:
        errors.append(
            "gates.current_evidence.results PIT compared case count does not equal required case count"
        )
    if summary.get("non_passed_pit_case_count") != 0:
        errors.append(
            "gates.current_evidence.results PIT non-passed case count is not zero"
        )
    return errors


def broad_e2e_section_errors(current: dict[str, Any]) -> list[str]:
    broad_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "e2e-broad-parity"
            and result.get("name")
            == "broad_unified_opensearch_e2e_report_has_no_failed_missing_or_drifted_required_suites"
        ):
            broad_result = result
            break
    if broad_result is None:
        return ["gates.current_evidence.results broad E2E section result is missing"]
    summary = broad_result.get("summary")
    if not isinstance(summary, dict):
        return ["gates.current_evidence.results broad E2E section summary is missing"]

    errors: list[str] = []
    expected_sections = {
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    }
    required_sections = summary.get("required_sections")
    if set(required_sections or []) != expected_sections:
        errors.append("gates.current_evidence.results broad E2E required sections mismatch")
    if summary.get("required_section_count") != len(expected_sections):
        errors.append("gates.current_evidence.results broad E2E required section count mismatch")
    suite_counts = summary.get("required_section_suite_counts")
    report_path_counts = summary.get("required_section_report_path_counts")
    if not isinstance(suite_counts, dict):
        errors.append("gates.current_evidence.results broad E2E section suite counts are missing")
    if not isinstance(report_path_counts, dict):
        errors.append("gates.current_evidence.results broad E2E section report path counts are missing")
    if isinstance(suite_counts, dict) and isinstance(report_path_counts, dict):
        for section in sorted(expected_sections):
            suite_count = suite_counts.get(section)
            report_path_count = report_path_counts.get(section)
            if not isinstance(suite_count, int) or suite_count <= 0:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} suite count is not positive"
                )
            if not isinstance(report_path_count, int) or report_path_count <= 0:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} report path count is not positive"
                )
            if isinstance(suite_count, int) and isinstance(report_path_count, int) and suite_count != report_path_count:
                errors.append(
                    f"gates.current_evidence.results broad E2E {section} suite/report path count mismatch"
                )
    return errors


def mixed_cluster_coverage_errors(current: dict[str, Any]) -> list[str]:
    coverage_result = None
    remote_pit_result = None
    for result in current.get("results") or []:
        if not isinstance(result, dict):
            continue
        if (
            result.get("group") == "mixed-cluster-coverage-current"
            and result.get("name")
            == "mixed_cluster_join_and_movement_coverage_is_reported_with_scope_boundary"
        ):
            coverage_result = result
        if (
            result.get("group") == "mixed-cluster-coverage-current"
            and result.get("name")
            == "multi_node_transport_admin_report_requires_remote_pit_forwarding_cases"
        ):
            remote_pit_result = result

    errors: list[str] = []
    if coverage_result is None:
        errors.append("gates.current_evidence.results mixed-cluster coverage result is missing")
    else:
        coverage_summary = coverage_result.get("summary")
        if not isinstance(coverage_summary, dict):
            errors.append("gates.current_evidence.results mixed-cluster coverage summary is missing")
        else:
            errors.extend(mixed_cluster_coverage_summary_errors(coverage_summary))

    if remote_pit_result is None:
        errors.append("gates.current_evidence.results mixed-cluster remote PIT result is missing")
    else:
        remote_pit_summary = remote_pit_result.get("summary")
        if not isinstance(remote_pit_summary, dict):
            errors.append("gates.current_evidence.results mixed-cluster remote PIT summary is missing")
        else:
            if remote_pit_summary.get("passed") is not True:
                errors.append("gates.current_evidence.results mixed-cluster remote PIT did not pass")
            if remote_pit_summary.get("remote_pit_required") is not True:
                errors.append("gates.current_evidence.results mixed-cluster remote PIT is not required")
            remote_pit_case_count = remote_pit_summary.get("remote_pit_case_count")
            if not isinstance(remote_pit_case_count, int) or remote_pit_case_count <= 0:
                errors.append(
                    "gates.current_evidence.results mixed-cluster remote PIT case count is not positive"
                )
            if remote_pit_summary.get("failed_count") != 0:
                errors.append(
                    "gates.current_evidence.results mixed-cluster remote PIT failed count is not zero"
                )

    return errors


def mixed_cluster_coverage_summary_errors(summary: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if summary.get("passed") is not True:
        errors.append("gates.current_evidence.results mixed-cluster coverage did not pass")
    phase_c_report_count = summary.get("phase_c_report_count")
    phase_c_passed_count = summary.get("phase_c_passed_report_count")
    phase_c_fresh_count = summary.get("phase_c_fresh_report_count")
    if not isinstance(phase_c_report_count, int) or phase_c_report_count <= 0:
        errors.append("gates.current_evidence.results mixed-cluster phase C report count is not positive")
    if phase_c_passed_count != phase_c_report_count:
        errors.append("gates.current_evidence.results mixed-cluster phase C passed count mismatch")
    if phase_c_fresh_count != phase_c_report_count:
        errors.append("gates.current_evidence.results mixed-cluster phase C fresh count mismatch")

    failure_node_loss_count = summary.get("failure_node_loss_report_count")
    failure_node_loss_passed_count = summary.get("failure_node_loss_passed_report_count")
    if not isinstance(failure_node_loss_count, int) or failure_node_loss_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss report count is not positive"
        )
    if failure_node_loss_passed_count != failure_node_loss_count:
        errors.append(
            "gates.current_evidence.results mixed-cluster failure node-loss passed count mismatch"
        )

    required_true_flags = (
        "shard_movement_passed",
        "shard_movement_fresh",
        "checkpoint_drift_ok",
        "checkpoint_monotonicity_ok",
        "opensearch_to_steelsearch_passed",
        "retention_lease_metadata_ok",
        "steelsearch_to_opensearch_passed",
        "transport_log_ok",
        "unsupported_allocation_explain_ok",
    )
    for flag in required_true_flags:
        if summary.get(flag) is not True:
            errors.append(f"gates.current_evidence.results mixed-cluster {flag} is not true")

    shard_phase_count = summary.get("shard_movement_phase_count")
    required_phase_count = summary.get("shard_movement_required_phase_count")
    required_interruption_count = summary.get("shard_movement_required_interruption_phase_count")
    if not isinstance(shard_phase_count, int) or shard_phase_count <= 0:
        errors.append("gates.current_evidence.results mixed-cluster shard movement phase count is not positive")
    if not isinstance(required_phase_count, int) or required_phase_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster required shard movement phase count is not positive"
        )
    elif isinstance(shard_phase_count, int) and shard_phase_count < required_phase_count:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase count is below required count"
        )
    if not isinstance(required_interruption_count, int) or required_interruption_count <= 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster required interruption phase count is not positive"
        )
    if summary.get("shard_movement_missing_required_phase_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster missing required shard movement phase count is not zero"
        )
    if summary.get("shard_movement_phase_assertion_error_count") != 0:
        errors.append(
            "gates.current_evidence.results mixed-cluster shard movement phase assertion error count is not zero"
        )

    claim_boundary = summary.get("claim_boundary")
    if not isinstance(claim_boundary, str) or "mixed-cluster" not in claim_boundary:
        errors.append("gates.current_evidence.results mixed-cluster claim boundary is missing")
    return errors


if __name__ == "__main__":
    sys.exit(main())
