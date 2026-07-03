#!/usr/bin/env python3
"""Report OpenSearch transport action inventory and current interop evidence."""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/rust-port/generated/source-transport-actions.tsv"
DEFAULT_PEER_REPORT = ROOT / "target/runtime-peer-backpressure-current.json"
DEFAULT_ACCEPTED_EVIDENCE = ROOT / "tools/fixtures/interop-accepted-transport-action-evidence.json"
DEFAULT_ACTION_INVENTORY = ROOT / "tools/fixtures/interop-transport-action-inventory.json"
HANDSHAKE_MATRIX = ROOT / "docs/rust-port/transport-handshake-version-skew-matrix.md"
MESSAGE_SEQUENCE = ROOT / "docs/rust-port/transport-message-sequence.md"
ACCEPTED_EVIDENCE_SCOPES = {
    "bounded_local_subset",
    "bounded_seed_peer_fanout_subset",
    "fail_closed_or_empty_subset",
    "bounded_execution_boundary",
}
ACCEPTED_EVIDENCE_REQUIRED_FIELDS = (
    "evidence_kind",
    "request_evidence",
    "response_evidence",
)
ACCEPTED_EVIDENCE_POINTER_FIELDS = (
    "request_evidence",
    "response_evidence",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--peer-backpressure-report", default=str(DEFAULT_PEER_REPORT))
    parser.add_argument("--accepted-evidence", default=str(DEFAULT_ACCEPTED_EVIDENCE))
    parser.add_argument("--inventory", default=str(DEFAULT_ACTION_INVENTORY))
    parser.add_argument("--output")
    parser.add_argument("--require-peer-backpressure", action="store_true")
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="fail if peer backpressure evidence is older than this many seconds",
    )
    args = parser.parse_args()

    actions = load_actions(Path(args.source))
    inventory_path = Path(args.inventory)
    inventory = load_optional_json(inventory_path)
    accepted_evidence_path = Path(args.accepted_evidence)
    accepted_evidence = load_optional_json(accepted_evidence_path)
    peer_path = Path(args.peer_backpressure_report)
    peer_report = load_optional_json(peer_path)
    peer_fresh = report_fresh(peer_path, args.max_report_age_seconds)
    errors: list[str] = []
    if args.require_peer_backpressure and not peer_report_passed(peer_report):
        errors.append("peer backpressure report is missing or not passed")
    if args.require_peer_backpressure and not peer_fresh["fresh"]:
        errors.append(peer_fresh["reason"])
    evidence_errors = accepted_evidence_errors(accepted_evidence)
    errors.extend(evidence_errors)
    evidence_inventory = accepted_evidence_inventory_coverage(inventory, accepted_evidence)
    errors.extend(evidence_inventory["errors"])

    protocol_evidence = {
        "handshake_version_skew_matrix": file_evidence(HANDSHAKE_MATRIX),
        "transport_message_sequence": file_evidence(MESSAGE_SEQUENCE),
        "peer_backpressure": {
            "path": str(peer_path),
            "present": peer_report is not None,
            "passed": peer_report_passed(peer_report),
            "fresh": peer_fresh["fresh"],
            "age_seconds": peer_fresh["age_seconds"],
            "max_age_seconds": peer_fresh["max_age_seconds"],
            "profile": (peer_report or {}).get("summary", {}).get("profile"),
            "scope": (peer_report or {}).get("profile", {}).get("scope"),
        },
    }

    status = "ok" if not errors else "failed"
    implemented_count = count_status(actions, "implemented")
    partial_count = count_status(actions, "partial")
    planned_count = count_status(actions, "planned")
    stubbed_count = count_status(actions, "stubbed")
    out_of_scope_count = count_status(actions, "out-of-scope")
    report = {
        "status": status,
        "errors": errors,
        "source": str(Path(args.source)),
        "inventory_source": str(inventory_path),
        "accepted_evidence_source": str(accepted_evidence_path),
        "summary": {
            "passed": not errors,
            "transport_action_count": len(actions),
            "implemented_action_count": implemented_count,
            "partial_action_count": partial_count,
            "planned_action_count": planned_count,
            "stubbed_action_count": stubbed_count,
            "out_of_scope_action_count": out_of_scope_count,
            "action_coverage_claim": action_coverage_claim(implemented_count, partial_count),
            "peer_backpressure_passed": protocol_evidence["peer_backpressure"]["passed"],
            "accepted_evidence_action_count": accepted_evidence_action_count(accepted_evidence),
            "accepted_evidence_scope_counts": accepted_evidence_scope_counts(accepted_evidence),
            "inventory_action_count": evidence_inventory["inventory_action_count"],
            "accepted_evidence_inventory_matched_action_count": evidence_inventory["matched_action_count"],
            "accepted_evidence_inventory_missing_action_count": len(evidence_inventory["missing_actions"]),
            "accepted_evidence_inventory_extra_action_count": len(evidence_inventory["extra_actions"]),
        },
        "status_counts": status_counts(actions),
        "protocol_evidence": protocol_evidence,
        "actions": actions,
        "implemented_actions": filter_status(actions, "implemented"),
        "partial_actions": filter_status(actions, "partial"),
        "planned_actions": filter_status(actions, "planned"),
        "stubbed_actions": filter_status(actions, "stubbed"),
        "out_of_scope_actions": filter_status(actions, "out-of-scope"),
        "accepted_transport_evidence": accepted_evidence_actions(accepted_evidence),
        "accepted_evidence_inventory_coverage": evidence_inventory,
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


def accepted_evidence_actions(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    actions = report.get("actions")
    return actions if isinstance(actions, list) else []


def accepted_evidence_action_count(report: dict[str, Any] | None) -> int:
    return len(accepted_evidence_actions(report))


def inventory_action_names(report: dict[str, Any] | None) -> set[str]:
    if not isinstance(report, dict):
        return set()
    names = set()
    for action in report.get("actions") or []:
        if isinstance(action, dict) and action.get("action_name"):
            names.add(str(action["action_name"]))
    return names


def accepted_evidence_action_names(report: dict[str, Any] | None) -> set[str]:
    return {
        str(action["action_name"])
        for action in accepted_evidence_actions(report)
        if isinstance(action, dict) and action.get("action_name")
    }


def accepted_evidence_inventory_coverage(
    inventory: dict[str, Any] | None,
    accepted_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    inventory_names = inventory_action_names(inventory)
    evidence_names = accepted_evidence_action_names(accepted_evidence)
    missing = sorted(inventory_names - evidence_names)
    extra = sorted(evidence_names - inventory_names)
    errors = []
    if not isinstance(inventory, dict):
        errors.append("transport action inventory is missing or invalid")
    if missing:
        errors.append(f"accepted transport evidence is missing inventory actions: {', '.join(missing)}")
    if extra:
        errors.append(f"accepted transport evidence has actions outside inventory: {', '.join(extra)}")
    return {
        "inventory_action_count": len(inventory_names),
        "matched_action_count": len(inventory_names & evidence_names),
        "missing_actions": missing,
        "extra_actions": extra,
        "errors": errors,
    }


def accepted_evidence_scope_counts(report: dict[str, Any] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in accepted_evidence_actions(report):
        if not isinstance(action, dict):
            scope = "invalid"
        else:
            scope = str(action.get("execution_scope") or "missing")
        counts[scope] = counts.get(scope, 0) + 1
    return dict(sorted(counts.items()))


def accepted_evidence_errors(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return ["accepted transport evidence ledger is missing or invalid"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, action in enumerate(accepted_evidence_actions(report)):
        if not isinstance(action, dict):
            errors.append(f"accepted transport evidence row {index} is not an object")
            continue
        action_name = str(action.get("action_name") or "")
        if not action_name:
            errors.append(f"accepted transport evidence row {index} is missing action_name")
        elif action_name in seen:
            errors.append(f"duplicate accepted transport evidence action {action_name}")
        else:
            seen.add(action_name)
        if action.get("disposition") != "implemented":
            errors.append(f"{action_name or index}: accepted evidence disposition must be implemented")
        scope = action.get("execution_scope")
        if scope not in ACCEPTED_EVIDENCE_SCOPES:
            errors.append(f"{action_name or index}: unexpected execution_scope {scope!r}")
        if "full_parity" in str(scope):
            errors.append(f"{action_name or index}: accepted evidence must not claim full parity")
        for field in ACCEPTED_EVIDENCE_REQUIRED_FIELDS:
            if not isinstance(action.get(field), str) or not action.get(field):
                errors.append(f"{action_name or index}: accepted evidence is missing {field}")
                continue
            if field not in ACCEPTED_EVIDENCE_POINTER_FIELDS:
                continue
            path = evidence_pointer_path(action[field])
            if path is not None and not path.is_file():
                errors.append(
                    f"{action_name or index}: accepted evidence {field} points to missing file {path}"
                )
                continue
            symbol = evidence_pointer_symbol(action[field])
            if not symbol:
                errors.append(f"{action_name or index}: accepted evidence {field} is missing symbol")
                continue
            if path is not None and symbol not in path.read_text(encoding="utf-8", errors="ignore"):
                errors.append(
                    f"{action_name or index}: accepted evidence {field} symbol {symbol} not found in {path}"
                )
    return errors


def evidence_pointer_path(pointer: str) -> Path | None:
    path_text = pointer.split("::", 1)[0]
    if not path_text:
        return None
    path = Path(path_text)
    if path.is_absolute():
        return path
    return ROOT / path


def evidence_pointer_symbol(pointer: str) -> str:
    if "::" not in pointer:
        return ""
    return pointer.split("::", 1)[1]


def report_fresh(path: Path, max_age_seconds: float | None) -> dict[str, Any]:
    if max_age_seconds is None:
        return {
            "fresh": True,
            "age_seconds": None,
            "max_age_seconds": None,
            "reason": "",
        }
    if not path.is_file():
        return {
            "fresh": False,
            "age_seconds": None,
            "max_age_seconds": max_age_seconds,
            "reason": f"{path} is missing",
        }
    age_seconds = time.time() - path.stat().st_mtime
    return {
        "fresh": age_seconds <= max_age_seconds,
        "age_seconds": round(age_seconds, 3),
        "max_age_seconds": max_age_seconds,
        "reason": (
            ""
            if age_seconds <= max_age_seconds
            else f"{path} is stale: age_seconds={age_seconds:.0f} max_age_seconds={max_age_seconds:.0f}"
        ),
    }


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


def filter_status(actions: list[dict[str, str]], status: str) -> list[dict[str, str]]:
    return [action for action in actions if action["status"] == status]


def status_counts(actions: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in actions:
        status = action["status"] or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def action_coverage_claim(implemented_count: int, partial_count: int = 0) -> str:
    if implemented_count == 0:
        if partial_count:
            return (
                "OpenSearch ActionModule transport coverage has no implemented adapters yet; "
                "partial actions have explicit fail-closed or narrower execution boundaries"
            )
        return (
            "no OpenSearch ActionModule transport action is currently classified as implemented; "
            "current evidence covers frame/handshake/observe-only and query-phase backpressure surfaces"
        )
    return (
        "OpenSearch ActionModule transport coverage includes implemented adapters plus explicit "
        "fail-closed partial boundaries; inspect status_counts for the current split"
    )


if __name__ == "__main__":
    sys.exit(main())
