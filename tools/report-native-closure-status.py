#!/usr/bin/env python3
"""Report current native-closure gate status and final cutover readiness."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FINAL_CUTOVER_ITEMS = (
    "benchmark_coverage",
    "load_test_coverage",
    "chaos_test_coverage",
    "packaging_verified",
    "rolling_upgrade_coverage",
)
FINAL_CUTOVER_ITEM_INPUTS = {
    "benchmark_coverage": {
        "attach_argument": "--benchmark-report",
        "artifact_kind": "benchmark JSONL",
    },
    "load_test_coverage": {
        "attach_argument": "--load-report",
        "artifact_kind": "load JSON",
    },
    "chaos_test_coverage": {
        "attach_argument": "--chaos-report",
        "artifact_kind": "chaos JSON",
    },
    "packaging_verified": {
        "attach_argument": "--packaging-report",
        "artifact_kind": "packaging JSON",
    },
    "rolling_upgrade_coverage": {
        "attach_argument": "--rolling-upgrade-report",
        "artifact_kind": "rolling-upgrade JSON",
    },
}
READINESS_ATTACHMENT_INPUTS = {
    **FINAL_CUTOVER_ITEM_INPUTS,
    "load_comparison": {
        "attach_argument": "--load-comparison-report",
        "artifact_kind": "Steelsearch-vs-OpenSearch load comparison JSON",
    },
}
RELEASE_RECORD_ITEMS = (
    *READINESS_ATTACHMENT_INPUTS,
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-readiness-file", type=Path)
    parser.add_argument("--readiness-report", type=Path)
    parser.add_argument(
        "--current-evidence-report",
        type=Path,
        help="reuse current-evidence and runtime peer-backpressure gates from an existing native-closure status report",
    )
    parser.add_argument("--release-evidence-root", type=Path, default=ROOT / "target")
    parser.add_argument("--release-evidence-max-age-seconds", type=float, default=86_400.0)
    parser.add_argument("--output", type=Path, help="write the JSON status report to this path")
    parser.add_argument(
        "--require-final-cutover",
        action="store_true",
        help="exit non-zero unless release-readiness evidence is complete",
    )
    args = parser.parse_args()

    if args.current_evidence_report:
        current_evidence, peer_backpressure = load_current_evidence_gates(
            args.current_evidence_report
        )
    else:
        current_evidence = run_validation_batch("current-evidence-gate")
        peer_backpressure = run_validation_batch("runtime-peer-backpressure-current")
    final_cutover = inspect_release_readiness(
        args.release_readiness_file,
        readiness_report_path=args.readiness_report,
        evidence_root=args.release_evidence_root,
        evidence_max_age_seconds=args.release_evidence_max_age_seconds,
    )
    report = build_status_report(
        current_evidence=current_evidence,
        peer_backpressure=peer_backpressure,
        final_cutover=final_cutover,
        require_final_cutover=args.require_final_cutover,
        metadata=build_metadata(),
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["summary"]["passed"] else 1


def load_current_evidence_gates(path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    gates = payload.get("gates") if isinstance(payload.get("gates"), dict) else {}
    current = gates.get("current_evidence")
    peer = gates.get("runtime_peer_backpressure_current")
    return (
        current if isinstance(current, dict) else {"passed": False},
        peer if isinstance(peer, dict) else {"passed": False},
    )


def run_validation_batch(batch: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "tools/run-native-closure-validation.py",
        "--batch",
        batch,
        "--format",
        "json",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    payload = parse_json_payload(completed.stdout)
    summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
    results = payload.get("results", []) if isinstance(payload, dict) else []
    result_entries = [
        {
            "group": result.get("group"),
            "name": result.get("name"),
            "status": result.get("status"),
            "ok": result.get("ok"),
            "returncode": result.get("returncode"),
            "summary": result.get("summary", {}),
        }
        for result in results
        if isinstance(result, dict)
    ]
    return {
        "name": batch,
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and int(summary.get("failed_count") or 0) == 0,
        "summary": summary,
        "required_groups": list(CURRENT_EVIDENCE_GROUPS) if batch == "current-evidence-gate" else [],
        "groups": group_statuses(result_entries),
        "results": result_entries,
    }


def inspect_release_readiness(
    path: Path | None,
    *,
    readiness_report_path: Path | None = None,
    evidence_root: Path | None = None,
    evidence_max_age_seconds: float = 86_400.0,
) -> dict[str, Any]:
    evidence_inventory = inspect_release_evidence_inventory(
        evidence_root or ROOT / "target",
        max_age_seconds=evidence_max_age_seconds,
    )
    if path is None:
        return {
            "name": "release-readiness",
            "passed": False,
            "status": "pending",
            "reason": "release readiness manifest was not provided",
            "required_items": list(FINAL_CUTOVER_ITEMS),
            "startup_manifest_items": list(FINAL_CUTOVER_ITEMS),
            "missing_items": list(FINAL_CUTOVER_ITEMS),
            "required_item_inputs": final_cutover_item_inputs(list(FINAL_CUTOVER_ITEMS)),
            "readiness_attachment_items": list(READINESS_ATTACHMENT_INPUTS),
            "readiness_report_path": str(readiness_report_path) if readiness_report_path else None,
            "readiness_attachment_missing_items": list(READINESS_ATTACHMENT_INPUTS),
            "release_record_missing_items": list(RELEASE_RECORD_ITEMS),
            "readiness_attachment_inputs": READINESS_ATTACHMENT_INPUTS,
            "evidence_inventory": evidence_inventory,
            "manifest_command_template": release_readiness_manifest_command_template(),
        }
    command = [
        sys.executable,
        "tools/check-release-readiness-evidence.py",
        str(path),
        "--require-passed",
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    payload = parse_json_payload(completed.stdout)
    missing_items = missing_release_items(payload) if isinstance(payload, dict) else list(FINAL_CUTOVER_ITEMS)
    readiness_attachment = inspect_readiness_attachments(
        readiness_report_path=readiness_report_path,
        missing_startup_items=missing_items,
    )
    inventory_summary = evidence_inventory.get("summary", {})
    inventory_complete = (
        isinstance(inventory_summary, dict)
        and evidence_inventory.get("returncode") == 0
        and inventory_summary.get("complete") is True
    )
    release_record_missing_items = release_record_missing_items_from_inventory(evidence_inventory)
    inventory_errors = release_inventory_errors(evidence_inventory)
    passed = (
        completed.returncode == 0
        and not readiness_attachment["missing_items"]
        and inventory_complete
    )
    return {
        "name": "release-readiness",
        "command": command,
        "returncode": completed.returncode,
        "passed": passed,
        "status": "ok" if passed else "failed",
        "summary": payload.get("summary", {}) if isinstance(payload, dict) else {},
        "errors": payload.get("errors", []) if isinstance(payload, dict) else [],
        "required_items": list(FINAL_CUTOVER_ITEMS),
        "startup_manifest_items": list(FINAL_CUTOVER_ITEMS),
        "missing_items": missing_items,
        "required_item_inputs": final_cutover_item_inputs(missing_items),
        "readiness_attachment_items": list(READINESS_ATTACHMENT_INPUTS),
        "readiness_report_path": str(readiness_report_path) if readiness_report_path else None,
        "readiness_attachment_missing_items": readiness_attachment["missing_items"],
        "release_record_missing_items": release_record_missing_items,
        "readiness_attachment_errors": [*readiness_attachment["errors"], *inventory_errors],
        "readiness_attachment_inputs": READINESS_ATTACHMENT_INPUTS,
        "evidence_inventory": evidence_inventory,
        "manifest_command_template": release_readiness_manifest_command_template(),
    }


def inspect_release_evidence_inventory(root: Path, *, max_age_seconds: float) -> dict[str, Any]:
    command = [
        sys.executable,
        "tools/report-release-evidence-inventory.py",
        "--root",
        str(root),
        "--max-age-seconds",
        str(max_age_seconds),
    ]
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    payload = parse_json_payload(completed.stdout)
    return {
        "command": command,
        "returncode": completed.returncode,
        "summary": payload.get("summary", {}) if isinstance(payload, dict) else {},
        "attach_command_template": payload.get("attach_command_template", []) if isinstance(payload, dict) else [],
    }


def release_inventory_errors(inventory: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if inventory.get("returncode") != 0:
        errors.append(f"release evidence inventory failed: returncode={inventory.get('returncode')}")
    summary = inventory.get("summary")
    if not isinstance(summary, dict):
        errors.append("release evidence inventory summary is missing")
        return errors
    if summary.get("complete") is not True:
        errors.append("release evidence inventory is incomplete")
    startup_missing = summary.get("startup_missing_items")
    if isinstance(startup_missing, list) and startup_missing:
        errors.append(f"release evidence inventory startup_missing_items={','.join(startup_missing)}")
    attachment_missing = summary.get("readiness_attachment_missing_items")
    if isinstance(attachment_missing, list) and attachment_missing:
        errors.append(
            f"release evidence inventory readiness_attachment_missing_items={','.join(attachment_missing)}"
        )
    release_record_missing = summary.get("release_record_missing_items")
    if isinstance(release_record_missing, list) and release_record_missing:
        errors.append(
            f"release evidence inventory release_record_missing_items={','.join(release_record_missing)}"
        )
    return errors


def release_record_missing_items_from_inventory(inventory: dict[str, Any]) -> list[str]:
    summary = inventory.get("summary")
    if not isinstance(summary, dict):
        return list(RELEASE_RECORD_ITEMS)
    missing_items = summary.get("release_record_missing_items")
    if not isinstance(missing_items, list):
        return list(RELEASE_RECORD_ITEMS)
    return missing_items


def build_status_report(
    *,
    current_evidence: dict[str, Any],
    peer_backpressure: dict[str, Any],
    final_cutover: dict[str, Any],
    require_final_cutover: bool,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_ready = current_evidence_gate_ready(current_evidence) and bool(peer_backpressure.get("passed"))
    final_ready = bool(final_cutover.get("passed"))
    passed = current_ready and (final_ready or not require_final_cutover)
    return {
        "metadata": metadata or {},
        "summary": {
            "passed": passed,
            "current_evidence_ready": current_ready,
            "runtime_peer_backpressure_ready": bool(peer_backpressure.get("passed")),
            "final_cutover_ready": final_ready,
            "final_cutover_required": require_final_cutover,
            "status": status_name(current_ready, final_ready, require_final_cutover),
        },
        "gates": {
            "current_evidence": current_evidence,
            "runtime_peer_backpressure_current": peer_backpressure,
            "final_cutover": final_cutover,
        },
    }


def group_statuses(results: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for result in results:
        group = result.get("group")
        if not isinstance(group, str) or not group:
            continue
        groups[group] = {
            "ok": result.get("ok") is True,
            "status": result.get("status"),
            "returncode": result.get("returncode"),
        }
    return groups


def current_evidence_gate_ready(current_evidence: dict[str, Any]) -> bool:
    if current_evidence.get("passed") is not True:
        return False
    groups = current_evidence.get("groups")
    if not isinstance(groups, dict):
        return True
    return all(
        isinstance(groups.get(group), dict) and groups[group].get("ok") is True
        for group in CURRENT_EVIDENCE_GROUPS
    )


def build_metadata() -> dict[str, Any]:
    git_status_short = git_output("status", "--short")
    return {
        "generated_at_epoch_seconds": int(time.time()),
        "git_head": git_output("rev-parse", "HEAD"),
        "git_clean": git_status_short == "",
        "git_status_short": git_status_short,
    }


def git_output(*args: str) -> str | None:
    completed = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def status_name(current_ready: bool, final_ready: bool, require_final_cutover: bool) -> str:
    if not current_ready:
        return "failed"
    if final_ready:
        return "ready"
    if require_final_cutover:
        return "final-cutover-missing"
    return "current-evidence-ready-final-cutover-pending"


def missing_release_items(payload: dict[str, Any]) -> list[str]:
    items = payload.get("items") if isinstance(payload.get("items"), dict) else {}
    missing = []
    for name in FINAL_CUTOVER_ITEMS:
        item = items.get(name)
        if not isinstance(item, dict) or item.get("passed") is not True or item.get("errors"):
            missing.append(name)
    return missing


def final_cutover_item_inputs(item_names: list[str]) -> dict[str, dict[str, str]]:
    return {
        name: FINAL_CUTOVER_ITEM_INPUTS[name]
        for name in item_names
        if name in FINAL_CUTOVER_ITEM_INPUTS
    }


def inspect_readiness_attachments(
    *,
    readiness_report_path: Path | None,
    missing_startup_items: list[str],
) -> dict[str, Any]:
    missing = list(missing_startup_items)
    errors: list[str] = []
    if readiness_report_path is None:
        if "load_comparison" not in missing:
            missing.append("load_comparison")
        errors.append("readiness report path is not configured")
        return {"missing_items": missing, "errors": errors}

    try:
        report = json.loads(readiness_report_path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - final status reports blockers
        if "load_comparison" not in missing:
            missing.append("load_comparison")
        errors.append(f"failed to parse readiness report: {error}")
        return {"missing_items": missing, "errors": errors}

    evidence = readiness_release_evidence(report)
    if not isinstance(evidence, dict):
        if "load_comparison" not in missing:
            missing.append("load_comparison")
        errors.append("readiness report release evidence is missing")
        return {"missing_items": missing, "errors": errors}

    load_comparison = evidence.get("load_comparison")
    if not evidence_item_ready(
        load_comparison,
        base_dir=readiness_report_path.parent,
    ):
        if "load_comparison" not in missing:
            missing.append("load_comparison")
        errors.append("readiness report load_comparison evidence is not ready")
    return {"missing_items": missing, "errors": errors}


def readiness_release_evidence(report: Any) -> dict[str, Any] | None:
    if not isinstance(report, dict):
        return None
    evidence = report.get("release_evidence")
    if isinstance(evidence, dict):
        return evidence
    categories = report.get("categories")
    if not isinstance(categories, dict):
        return None
    release = categories.get("release")
    if not isinstance(release, dict):
        return None
    nested = release.get("evidence")
    return nested if isinstance(nested, dict) else None


def evidence_item_ready(item: Any, *, base_dir: Path) -> bool:
    if not isinstance(item, dict) or item.get("ready") is not True:
        return False
    blockers = item.get("blockers")
    if blockers not in ([], None):
        return False
    path_value = item.get("path")
    if not isinstance(path_value, str) or not path_value:
        return False
    path = Path(path_value)
    if not path.is_absolute():
        path = base_dir / path
    return path.is_file()


def release_readiness_manifest_command_template() -> list[str]:
    return [
        "python3",
        "tools/attach-release-readiness-evidence.py",
        "--readiness-report",
        "<readiness-report.json>",
        "--benchmark-report",
        "<benchmark.jsonl>",
        "--load-report",
        "<load.json>",
        "--load-comparison-report",
        "<load-comparison.json>",
        "--chaos-report",
        "<chaos.json>",
        "--packaging-report",
        "<packaging.json>",
        "--rolling-upgrade-report",
        "<rolling-upgrade.json>",
        "--release-readiness-file",
        "<release-readiness.json>",
    ]


def parse_json_payload(output: str) -> dict[str, Any]:
    decoder = json.JSONDecoder()
    for index, char in enumerate(output):
        if char != "{":
            continue
        try:
            payload, _ = decoder.raw_decode(output[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            return payload
    return {}


if __name__ == "__main__":
    sys.exit(main())
