#!/usr/bin/env python3
"""Report OpenSearch transport action inventory and current interop evidence."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "docs/rust-port/generated/source-transport-actions.tsv"
DEFAULT_PEER_REPORT = ROOT / "target/runtime-peer-backpressure-current.json"
DEFAULT_ACCEPTED_EVIDENCE = ROOT / "tools/fixtures/interop-accepted-transport-action-evidence.json"
DEFAULT_RELEASE_EVIDENCE = ROOT / "tools/fixtures/transport-release-parity-evidence.json"
DEFAULT_ACTION_INVENTORY = ROOT / "tools/fixtures/interop-transport-action-inventory.json"
HANDSHAKE_MATRIX = ROOT / "docs/rust-port/transport-handshake-version-skew-matrix.md"
MESSAGE_SEQUENCE = ROOT / "docs/rust-port/transport-message-sequence.md"
MIXED_CLUSTER_FAILURE_PROFILE = ROOT / "tools/run_mixed_cluster_failure_profile.sh"
ACCEPTED_EVIDENCE_SCOPES = {
    "bounded_local_subset",
    "bounded_seed_peer_fanout_subset",
    "fail_closed_or_empty_subset",
    "bounded_execution_boundary",
}
SCOPED_EVIDENCE_SCOPES = {
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
    parser.add_argument("--release-evidence", default=str(DEFAULT_RELEASE_EVIDENCE))
    parser.add_argument("--inventory", default=str(DEFAULT_ACTION_INVENTORY))
    parser.add_argument("--output")
    parser.add_argument(
        "--summary-only",
        action="store_true",
        help="print only the status and summary instead of the full coverage report",
    )
    parser.add_argument("--require-peer-backpressure", action="store_true")
    parser.add_argument(
        "--require-release-parity",
        action="store_true",
        help="fail unless release parity evidence covers every source-derived implemented action",
    )
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
    release_evidence_path = Path(args.release_evidence)
    release_evidence = load_optional_json(release_evidence_path)
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
    accepted_binding_errors = transport_evidence_action_binding_errors(
        inventory,
        accepted_evidence,
        "accepted",
    )
    errors.extend(accepted_binding_errors)
    accepted_shared_pointer_errors = transport_evidence_shared_pointer_errors(
        accepted_evidence,
        "accepted",
    )
    errors.extend(accepted_shared_pointer_errors)
    source_evidence = source_implemented_evidence_coverage(actions, inventory, accepted_evidence)
    errors.extend(source_evidence["errors"])
    release_errors = release_evidence_errors(release_evidence)
    errors.extend(release_errors)
    release_inventory = release_evidence_inventory_coverage(inventory, release_evidence)
    errors.extend(release_inventory["errors"])
    release_binding_errors = transport_evidence_action_binding_errors(
        inventory,
        release_evidence,
        "release",
    )
    errors.extend(release_binding_errors)
    release_shared_pointer_errors = transport_evidence_shared_pointer_errors(
        release_evidence,
        "release",
    )
    errors.extend(release_shared_pointer_errors)
    release_parity_evidence = transport_release_parity_evidence(
        actions,
        inventory,
        release_evidence,
    )
    errors.extend(release_parity_evidence["errors"])
    if args.require_release_parity and not release_parity_evidence["complete"]:
        errors.append(
            "release transport parity evidence is incomplete: "
            f"matched_source_action_count={release_parity_evidence['matched_source_action_count']} "
            f"source_implemented_action_count={release_parity_evidence['source_implemented_action_count']} "
            f"missing_source_action_count={len(release_parity_evidence['missing_source_actions'])}"
        )
    evidence_scope_inventory_errors = accepted_evidence_scope_inventory_errors(inventory, accepted_evidence)
    errors.extend(evidence_scope_inventory_errors)
    evidence_profile_errors = accepted_evidence_profile_errors(
        accepted_evidence,
        read_text_if_file(MIXED_CLUSTER_FAILURE_PROFILE),
    )
    errors.extend(evidence_profile_errors)

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
        "release_evidence_source": str(release_evidence_path),
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
            "release_parity_evidence_complete": release_parity_evidence["complete"],
            "release_parity_action_count": release_parity_evidence["release_evidence_action_count"],
            "release_parity_source_matched_action_count": release_parity_evidence[
                "matched_source_action_count"
            ],
            "release_parity_source_missing_action_count": len(
                release_parity_evidence["missing_source_actions"]
            ),
            "release_evidence_inventory_matched_action_count": release_inventory[
                "matched_action_count"
            ],
            "release_evidence_inventory_missing_action_count": len(
                release_inventory["missing_actions"]
            ),
            "release_evidence_inventory_extra_action_count": len(
                release_inventory["extra_actions"]
            ),
            "accepted_evidence_action_binding_error_count": len(accepted_binding_errors),
            "release_evidence_action_binding_error_count": len(release_binding_errors),
            "accepted_evidence_shared_pointer_error_count": len(
                accepted_shared_pointer_errors
            ),
            "release_evidence_shared_pointer_error_count": len(
                release_shared_pointer_errors
            ),
            "inventory_action_count": evidence_inventory["inventory_action_count"],
            "accepted_evidence_inventory_matched_action_count": evidence_inventory["matched_action_count"],
            "accepted_evidence_inventory_missing_action_count": len(evidence_inventory["missing_actions"]),
            "accepted_evidence_inventory_extra_action_count": len(evidence_inventory["extra_actions"]),
            "source_implemented_inventory_matched_action_count": source_evidence[
                "matched_source_action_count"
            ],
            "source_implemented_inventory_missing_action_count": len(
                source_evidence["missing_inventory_actions"]
            ),
            "source_implemented_evidence_missing_action_count": len(
                source_evidence["missing_evidence_actions"]
            ),
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
        "release_evidence_inventory_coverage": release_inventory,
        "accepted_evidence_action_binding_errors": accepted_binding_errors,
        "release_evidence_action_binding_errors": release_binding_errors,
        "accepted_evidence_shared_pointer_errors": accepted_shared_pointer_errors,
        "release_evidence_shared_pointer_errors": release_shared_pointer_errors,
        "source_implemented_evidence_coverage": source_evidence,
        "release_parity_evidence": release_parity_evidence,
    }
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.summary_only:
        print(f"{report['status']}: {report['summary']}")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))
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


def read_text_if_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


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


def release_evidence_actions(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    actions = report.get("actions")
    return actions if isinstance(actions, list) else []


def release_evidence_action_names(report: dict[str, Any] | None) -> set[str]:
    return {
        str(action["action_name"])
        for action in release_evidence_actions(report)
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


def release_evidence_inventory_coverage(
    inventory: dict[str, Any] | None,
    release_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    inventory_names = inventory_action_names(inventory)
    evidence_names = release_evidence_action_names(release_evidence)
    missing = sorted(inventory_names - evidence_names)
    extra = sorted(evidence_names - inventory_names)
    errors = []
    if not isinstance(inventory, dict):
        errors.append("transport action inventory is missing or invalid")
    if missing:
        errors.append(
            f"release transport evidence is missing inventory actions: {', '.join(missing)}"
        )
    if extra:
        errors.append(
            f"release transport evidence has actions outside inventory: {', '.join(extra)}"
        )
    return {
        "inventory_action_count": len(inventory_names),
        "matched_action_count": len(inventory_names & evidence_names),
        "missing_actions": missing,
        "extra_actions": extra,
        "errors": errors,
    }


def transport_evidence_action_binding_errors(
    inventory: dict[str, Any] | None,
    evidence: dict[str, Any] | None,
    label: str,
) -> list[str]:
    inventory_by_name = inventory_actions_by_name(inventory)
    errors: list[str] = []
    for index, action in enumerate(evidence_actions(evidence)):
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("action_name") or index)
        inventory_action = inventory_by_name.get(action_name)
        if inventory_action is None:
            continue
        expected_tokens = transport_action_binding_tokens(inventory_action)
        pointer_text = evidence_pointer_binding_text(action)
        if expected_tokens and not any(token in pointer_text for token in expected_tokens):
            errors.append(
                f"{action_name}: {label} evidence pointers do not mention action metadata "
                f"tokens {sorted(expected_tokens)}"
            )
    return errors


def evidence_actions(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(report, dict):
        return []
    actions = report.get("actions")
    return actions if isinstance(actions, list) else []


def transport_action_binding_tokens(action: dict[str, Any]) -> set[str]:
    ignored = {"action", "request", "response", "transport"}
    tokens: set[str] = set()
    for field in (
        "action_type",
        "transport_action",
        "request_wire_type",
        "response_wire_type",
    ):
        for token in camel_case_tokens(str(action.get(field) or "")):
            if token not in ignored:
                tokens.add(token)
    return tokens


def camel_case_tokens(value: str) -> list[str]:
    return [
        token.lower()
        for token in re.findall(r"[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)|\d+", value)
        if token
    ]


def evidence_pointer_binding_text(action: dict[str, Any]) -> str:
    return " ".join(
        str(action.get(field) or "").replace("_", " ").lower()
        for field in ACCEPTED_EVIDENCE_POINTER_FIELDS
    )


def transport_evidence_shared_pointer_errors(
    evidence: dict[str, Any] | None,
    label: str,
) -> list[str]:
    errors: list[str] = []
    for index, action in enumerate(evidence_actions(evidence)):
        if not isinstance(action, dict):
            continue
        request_evidence = str(action.get("request_evidence") or "")
        response_evidence = str(action.get("response_evidence") or "")
        if not request_evidence or request_evidence != response_evidence:
            continue
        action_name = str(action.get("action_name") or index)
        symbol = evidence_pointer_symbol(request_evidence)
        if not runtime_semantic_symbol(symbol):
            errors.append(
                f"{action_name}: {label} evidence reuses one pointer for request and "
                "response without a runtime semantic symbol"
            )
    return errors


def runtime_semantic_symbol(symbol: str) -> bool:
    lowered = symbol.lower()
    return any(
        token in lowered
        for token in (
            "route",
            "queue",
            "gate",
            "fanout",
            "fans_out",
        )
    )


def source_implemented_evidence_coverage(
    source_actions: list[dict[str, str]],
    inventory: dict[str, Any] | None,
    accepted_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    inventory_by_type = inventory_actions_by_type(inventory)
    evidence_names = accepted_evidence_action_names(accepted_evidence)
    implemented = [
        action for action in source_actions if action.get("status") == "implemented"
    ]
    missing_inventory: list[dict[str, str]] = []
    missing_evidence: list[dict[str, Any]] = []
    matched = 0

    for action in implemented:
        action_type = action["action"].removesuffix(".INSTANCE")
        inventory_actions = inventory_by_type.get(action_type, [])
        if not inventory_actions:
            missing_inventory.append(action)
            continue
        matched += 1
        if not any(
            str(inventory_action.get("action_name") or "") in evidence_names
            for inventory_action in inventory_actions
        ):
            missing_evidence.append(
                {
                    "action": action["action"],
                    "source": action["source"],
                    "line": action["line"],
                    "inventory_action_names": [
                        inventory_action.get("action_name")
                        for inventory_action in inventory_actions
                    ],
                }
            )

    errors = []
    if missing_inventory:
        errors.append(
            "source implemented transport actions missing inventory mappings: "
            + ", ".join(action["action"] for action in missing_inventory[:10])
        )
    if missing_evidence:
        errors.append(
            "source implemented transport actions missing accepted evidence: "
            + ", ".join(action["action"] for action in missing_evidence[:10])
        )
    return {
        "source_implemented_action_count": len(implemented),
        "matched_source_action_count": matched,
        "missing_inventory_actions": missing_inventory,
        "missing_evidence_actions": missing_evidence,
        "errors": errors,
    }


def accepted_evidence_scope_inventory_errors(
    inventory: dict[str, Any] | None,
    accepted_evidence: dict[str, Any] | None,
) -> list[str]:
    inventory_by_name = inventory_actions_by_name(inventory)
    errors: list[str] = []
    for index, action in enumerate(accepted_evidence_actions(accepted_evidence)):
        if not isinstance(action, dict):
            continue
        scope = action.get("execution_scope")
        if scope != "bounded_seed_peer_fanout_subset":
            continue
        action_name = str(action.get("action_name") or index)
        inventory_action = inventory_by_name.get(action_name)
        if inventory_action is None:
            errors.append(
                f"{action_name}: bounded seed-peer fanout evidence is missing matching inventory action"
            )
            continue
        reason = str(inventory_action.get("reason") or "")
        if "fanout" not in reason and "seed-peer" not in reason:
            errors.append(
                f"{action_name}: bounded seed-peer fanout evidence requires inventory reason to describe fanout"
            )
    return errors


def accepted_evidence_profile_errors(
    accepted_evidence: dict[str, Any] | None,
    mixed_cluster_failure_profile: str | None,
) -> list[str]:
    errors: list[str] = []
    if mixed_cluster_failure_profile is None:
        return ["mixed-cluster failure profile script is missing"]
    for index, action in enumerate(accepted_evidence_actions(accepted_evidence)):
        if not isinstance(action, dict):
            continue
        if action.get("execution_scope") != "bounded_seed_peer_fanout_subset":
            continue
        action_name = str(action.get("action_name") or index)
        symbol = evidence_pointer_symbol(str(action.get("response_evidence") or ""))
        if not symbol:
            errors.append(
                f"{action_name}: bounded seed-peer fanout evidence is missing response evidence symbol"
            )
            continue
        if not mixed_cluster_failure_profile_runs_exact_test(mixed_cluster_failure_profile, symbol):
            errors.append(
                f"{action_name}: bounded seed-peer fanout evidence response test is not run exactly in mixed-cluster failure profile"
            )
    return errors


def mixed_cluster_failure_profile_runs_exact_test(profile: str, symbol: str) -> bool:
    for line in profile.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if (
            "cargo test" in stripped
            and symbol in stripped
            and "--exact" in stripped
        ):
            return True
    return False


def inventory_actions_by_name(report: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(report, dict):
        return {}
    return {
        str(action["action_name"]): action
        for action in report.get("actions") or []
        if isinstance(action, dict) and action.get("action_name")
    }


def inventory_actions_by_type(report: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    if not isinstance(report, dict):
        return {}
    by_type: dict[str, list[dict[str, Any]]] = {}
    for action in report.get("actions") or []:
        if not isinstance(action, dict) or not action.get("action_type"):
            continue
        by_type.setdefault(str(action["action_type"]), []).append(action)
    return by_type


def accepted_evidence_scope_counts(report: dict[str, Any] | None) -> dict[str, int]:
    counts: dict[str, int] = {}
    for action in accepted_evidence_actions(report):
        if not isinstance(action, dict):
            scope = "invalid"
        else:
            scope = str(action.get("execution_scope") or "missing")
        counts[scope] = counts.get(scope, 0) + 1
    return dict(sorted(counts.items()))


def transport_release_parity_evidence(
    source_actions: list[dict[str, str]],
    inventory: dict[str, Any] | None,
    release_evidence: dict[str, Any] | None,
) -> dict[str, Any]:
    inventory_by_type = inventory_actions_by_type(inventory)
    release_names = release_evidence_action_names(release_evidence)
    implemented_count = count_status(source_actions, "implemented")
    matched_source_actions = []
    missing_source_actions = []
    for action in source_actions:
        if action.get("status") != "implemented":
            continue
        action_type = action["action"].removesuffix(".INSTANCE")
        inventory_actions = inventory_by_type.get(action_type, [])
        if any(
            str(inventory_action.get("action_name") or "") in release_names
            for inventory_action in inventory_actions
        ):
            matched_source_actions.append(action)
        else:
            missing_source_actions.append(action)

    complete = (
        implemented_count > 0
        and not missing_source_actions
        and len(matched_source_actions) == implemented_count
    )
    blocking_reasons = []
    if missing_source_actions:
        blocking_reasons.append(
            "release transport evidence does not cover every source-derived implemented action"
        )
    return {
        "complete": complete,
        "source_implemented_action_count": implemented_count,
        "release_evidence_action_count": len(release_names),
        "matched_source_action_count": len(matched_source_actions),
        "missing_source_actions": missing_source_actions,
        "release_evidence_actions": sorted(release_names),
        "blocking_reasons": blocking_reasons,
        "errors": [],
    }


def release_evidence_errors(report: dict[str, Any] | None) -> list[str]:
    if not isinstance(report, dict):
        return ["release transport evidence ledger is missing or invalid"]
    errors: list[str] = []
    seen: set[str] = set()
    for index, action in enumerate(release_evidence_actions(report)):
        if not isinstance(action, dict):
            errors.append(f"release transport evidence row {index} is not an object")
            continue
        action_name = str(action.get("action_name") or "")
        if not action_name:
            errors.append(f"release transport evidence row {index} is missing action_name")
        elif action_name in seen:
            errors.append(f"duplicate release transport evidence action {action_name}")
        else:
            seen.add(action_name)
        if action.get("disposition") != "implemented":
            errors.append(f"{action_name or index}: release evidence disposition must be implemented")
        if action.get("execution_scope") != "runtime_action_parity":
            errors.append(
                f"{action_name or index}: release evidence execution_scope must be runtime_action_parity"
            )
        if action.get("evidence_kind") != "live_probe":
            errors.append(f"{action_name or index}: release evidence must use live_probe evidence")
        for field in ACCEPTED_EVIDENCE_POINTER_FIELDS:
            if not isinstance(action.get(field), str) or not action.get(field):
                errors.append(f"{action_name or index}: release evidence is missing {field}")
                continue
            path = evidence_pointer_path(action[field])
            if path is not None and not path.is_file():
                errors.append(
                    f"{action_name or index}: release evidence {field} points to missing file {path}"
                )
                continue
            symbol = evidence_pointer_symbol(action[field])
            if not symbol:
                errors.append(f"{action_name or index}: release evidence {field} is missing symbol")
                continue
            if path is not None and symbol not in path.read_text(encoding="utf-8", errors="ignore"):
                errors.append(
                    f"{action_name or index}: release evidence {field} symbol {symbol} not found in {path}"
                )
    return errors


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
        response_evidence = str(action.get("response_evidence") or "")
        if scope == "bounded_seed_peer_fanout_subset" and not (
            "fanout" in response_evidence or "fans_out" in response_evidence
        ):
            errors.append(
                f"{action_name or index}: bounded seed-peer fanout evidence must point to a fanout response test"
            )
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
        "OpenSearch ActionModule transport coverage includes implemented adapters with scoped "
        "execution evidence; inspect release_parity_evidence before making broad transport claims"
    )


if __name__ == "__main__":
    sys.exit(main())
