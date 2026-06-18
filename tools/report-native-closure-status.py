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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-readiness-file", type=Path)
    parser.add_argument("--output", type=Path, help="write the JSON status report to this path")
    parser.add_argument(
        "--require-final-cutover",
        action="store_true",
        help="exit non-zero unless release-readiness evidence is complete",
    )
    args = parser.parse_args()

    current_evidence = run_validation_batch("current-evidence-gate")
    peer_backpressure = run_validation_batch("runtime-peer-backpressure-current")
    final_cutover = inspect_release_readiness(args.release_readiness_file)
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
    return {
        "name": batch,
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0 and int(summary.get("failed_count") or 0) == 0,
        "summary": summary,
    }


def inspect_release_readiness(path: Path | None) -> dict[str, Any]:
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
            "readiness_attachment_inputs": READINESS_ATTACHMENT_INPUTS,
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
    return {
        "name": "release-readiness",
        "command": command,
        "returncode": completed.returncode,
        "passed": completed.returncode == 0,
        "status": "ok" if completed.returncode == 0 else "failed",
        "summary": payload.get("summary", {}) if isinstance(payload, dict) else {},
        "errors": payload.get("errors", []) if isinstance(payload, dict) else [],
        "required_items": list(FINAL_CUTOVER_ITEMS),
        "startup_manifest_items": list(FINAL_CUTOVER_ITEMS),
        "missing_items": missing_release_items(payload) if isinstance(payload, dict) else list(FINAL_CUTOVER_ITEMS),
        "required_item_inputs": final_cutover_item_inputs(
            missing_release_items(payload) if isinstance(payload, dict) else list(FINAL_CUTOVER_ITEMS)
        ),
        "readiness_attachment_items": list(READINESS_ATTACHMENT_INPUTS),
        "readiness_attachment_inputs": READINESS_ATTACHMENT_INPUTS,
        "manifest_command_template": release_readiness_manifest_command_template(),
    }


def build_status_report(
    *,
    current_evidence: dict[str, Any],
    peer_backpressure: dict[str, Any],
    final_cutover: dict[str, Any],
    require_final_cutover: bool,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    current_ready = bool(current_evidence.get("passed")) and bool(peer_backpressure.get("passed"))
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
