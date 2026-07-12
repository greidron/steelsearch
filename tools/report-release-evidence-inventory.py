#!/usr/bin/env python3
"""Inventory release-readiness evidence artifacts before final cutover."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any


STARTUP_ITEMS = {
    "benchmark_coverage": {
        "artifact_kind": "benchmark JSONL",
        "patterns": ("**/*benchmark*.jsonl",),
        "attach_argument": "--benchmark-report",
    },
    "load_test_coverage": {
        "artifact_kind": "load JSON",
        "patterns": ("**/*load-baseline*.json", "**/*load*baseline*.json"),
        "attach_argument": "--load-report",
    },
    "chaos_test_coverage": {
        "artifact_kind": "chaos JSON",
        "patterns": ("**/*chaos*.json",),
        "attach_argument": "--chaos-report",
    },
    "packaging_verified": {
        "artifact_kind": "packaging JSON",
        "patterns": ("**/*packaging*.json",),
        "attach_argument": "--packaging-report",
    },
    "rolling_upgrade_coverage": {
        "artifact_kind": "rolling-upgrade JSON",
        "patterns": ("**/*rolling*upgrade*.json", "**/*rolling*.json"),
        "attach_argument": "--rolling-upgrade-report",
    },
}
READINESS_ONLY_ITEMS = {
    "load_comparison": {
        "artifact_kind": "Steelsearch-vs-OpenSearch load comparison JSON",
        "patterns": ("**/*load-comparison*.json", "**/*load*comparison*.json"),
        "attach_argument": "--load-comparison-report",
    },
}
RELEASE_RECORD_ONLY_ITEMS = {
    "pit_e2e_coverage": {
        "artifact_kind": "PIT OpenSearch comparison E2E JSON",
        "patterns": (
            "**/unified-opensearch-e2e-pit*/unified-opensearch-e2e-report.json",
            "**/*pit*e2e*.json",
        ),
    },
    "promotion_gate_suite": {
        "artifact_kind": "promotion gate suite JSON",
        "patterns": ("**/*promotion-gate-suite*.json", "**/*promotion*gate*suite*.json"),
    },
}
ATTACHMENT_ITEMS = {**STARTUP_ITEMS, **READINESS_ONLY_ITEMS}
ALL_ITEMS = {**ATTACHMENT_ITEMS, **RELEASE_RECORD_ONLY_ITEMS}
REQUIRED_BENCHMARKS = {
    "index",
    "bulk",
    "refresh",
    "lexical_search",
    "aggregation",
    "exact_vector_search",
    "hnsw_vector_search",
    "hybrid_search",
    "nested_child_index_search",
}
REQUIRED_LOAD_OPERATIONS = {
    "write",
    "lexical",
    "facet",
    "ranking",
    "sort_filter",
    "vector",
    "hybrid",
    "nested",
    "refresh",
}
REQUIRED_LOAD_RESOURCE_COUNTERS = {
    "memory_rss_bytes",
    "vector_cache_bytes",
    "operation_log_bytes",
}
REQUIRED_ROLLING_UPGRADE_STEPS = [
    "cluster-ready-before",
    "node-1-upgrade",
    "cluster-ready-after-node-1",
    "node-2-upgrade",
    "cluster-ready-after-node-2",
    "node-3-upgrade",
    "cluster-ready-after-node-3",
]
REQUIRED_ROLLING_UPGRADE_ASSERTIONS = [
    "cluster ready before upgrade sequence",
    "upgrade steps recorded in order",
    "cluster ready after each upgraded node rejoins",
]
REQUIRED_PROMOTION_GATE_CHECKS = {
    "source-compatibility-drift",
    "source-compatibility-closure",
    "root-identity",
    "index-metadata",
    "document-write",
    "bulk",
    "cluster-admin",
    "search",
    "pit-e2e-coverage",
    "snapshot",
    "vector",
    "knn-plugin",
    "ml",
    "benchmark-evidence",
    "peer-node",
    "security-row-reclassification",
    "transport-action-coverage",
    "broad-unified-e2e-sections",
    "rest-api-live-source-coverage",
    "e2e-doc-current-counts",
    "runtime-control-surface-inventory",
    "mixed-cluster-coverage",
    "external-interop",
    "migration",
    "harness",
}
OPTIONAL_PROMOTION_GATE_CHECKS = {
    "release-evidence-inventory",
}
REQUIRED_PROMOTION_GATE_COMMAND_FRAGMENTS = {
    "benchmark-evidence": (
        "tools/check-benchmark-evidence.py",
        "--comparison-summary",
        "target/search-benchmark-matrix-current-20260630T023334Z/summary.json",
        "--max-age-seconds",
        "604800",
    ),
    "broad-unified-e2e-sections": (
        "tools/check-unified-opensearch-e2e-report.py",
        "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json",
        "--max-report-age-seconds",
        "604800",
        "--require-no-unresolved-skips",
        "route_parity",
        "semantic_parity",
        "durability_parity",
        "security_parity",
        "distributed_parity",
    ),
    "mixed-cluster-coverage": (
        "tools/report-mixed-cluster-coverage.py",
        "--require-passed",
        "--max-report-age-seconds",
        "604800",
        "--shard-movement-report",
        "target/three-node-shard-movement-interruption-current/report.json",
    ),
    "peer-node": (
        "tools/check-peer-node-promotion-gate.py",
        "--max-report-age-seconds",
        "604800",
    ),
    "pit-e2e-coverage": (
        "tools/check-pit-e2e-coverage.py",
        "target/unified-opensearch-e2e-pit-current/unified-opensearch-e2e-report.json",
        "--max-report-age-seconds",
        "604800",
        "--require-all-pit-passed",
    ),
    "rest-api-live-source-coverage": (
        "tools/report-rest-api-coverage.py",
        "target/unified-opensearch-e2e-broad-current/unified-opensearch-e2e-report.json",
        "--max-report-age-seconds",
        "604800",
        "--require-live-required-suites",
        "--min-live-required-matched-source-route-count",
        "378",
        "--min-live-required-matched-source-route-ratio",
        "1.0",
        "--min-source-route-count",
        "389",
        "--require-closed-source-statuses",
    ),
    "transport-action-coverage": (
        "tools/report-transport-action-coverage.py",
        "--require-peer-backpressure",
        "--require-release-parity",
        "--require-closed-action-statuses",
        "--max-report-age-seconds",
        "604800",
    ),
}

REQUIRED_PIT_CASES = {
    "search-compat": {
        "pit_open_search",
        "pit_search",
        "pit_list_search",
        "pit_clear_search",
        "pit_search_after_close_missing_context",
        "pit_shard_doc_search_after_search",
        "pit_snapshot_after_update_delete_search",
        "msearch_pit_snapshot_after_update_delete_search",
    },
    "search-strict": {
        "pit_open_search",
        "pit_search",
        "pit_list_search",
        "pit_clear_search",
        "pit_search_after_close_missing_context",
        "pit_shard_doc_search_after_search",
        "pit_snapshot_after_update_delete_search",
    },
    "search-semantic": {
        "pit_snapshot_after_update_delete_semantic",
        "pit_search_after_close_missing_context_semantic",
    },
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("target"))
    parser.add_argument("--max-age-seconds", type=float, default=86_400.0)
    parser.add_argument("--require-complete", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    report = build_inventory(
        args.root,
        max_age_seconds=args.max_age_seconds,
        require_complete=args.require_complete,
    )
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["summary"]["passed"] else 1


def build_inventory(
    root: Path,
    *,
    max_age_seconds: float,
    require_complete: bool = False,
    now: float | None = None,
) -> dict[str, Any]:
    now = time.time() if now is None else now
    root = root.resolve()
    items = {
        name: inspect_item(root, name, spec, max_age_seconds=max_age_seconds, now=now)
        for name, spec in ALL_ITEMS.items()
    }
    missing_startup = [
        name for name in STARTUP_ITEMS if not items[name]["ready"]
    ]
    missing_readiness = [
        name for name in ATTACHMENT_ITEMS if not items[name]["ready"]
    ]
    missing_release_record = [
        name for name in ALL_ITEMS if not items[name]["ready"]
    ]
    ready_startup = [
        name for name in STARTUP_ITEMS if items[name]["ready"]
    ]
    ready_readiness = [
        name for name in ATTACHMENT_ITEMS if items[name]["ready"]
    ]
    ready_release_record = [
        name for name in ALL_ITEMS if items[name]["ready"]
    ]
    complete = not missing_release_record
    passed = complete if require_complete else True
    return {
        "summary": {
            "passed": passed,
            "complete": complete,
            "require_complete": require_complete,
            "root": str(root),
            "max_age_seconds": max_age_seconds,
            "startup_item_count": len(STARTUP_ITEMS),
            "startup_ready_item_count": len(ready_startup),
            "readiness_attachment_item_count": len(ATTACHMENT_ITEMS),
            "release_record_item_count": len(ALL_ITEMS),
            "readiness_attachment_ready_item_count": len(ready_readiness),
            "release_record_ready_item_count": len(ready_release_record),
            "startup_ready_items": ready_startup,
            "startup_missing_items": missing_startup,
            "readiness_attachment_ready_items": ready_readiness,
            "readiness_attachment_missing_items": missing_readiness,
            "release_record_ready_items": ready_release_record,
            "release_record_missing_items": missing_release_record,
        },
        "items": items,
        "attach_command_template": attach_command_template(items),
    }


def inspect_item(
    root: Path,
    name: str,
    spec: dict[str, Any],
    *,
    max_age_seconds: float,
    now: float,
) -> dict[str, Any]:
    candidates = sorted(
        unique_paths(
            candidate
            for pattern in spec["patterns"]
            for candidate in root.glob(pattern)
            if candidate.is_file() and not excluded_candidate(candidate, spec)
        ),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    latest = candidates[0] if candidates else None
    blockers: list[str] = []
    if latest is None:
        blockers.append("artifact candidate is missing")
        age_seconds = None
    else:
        age_seconds = now - latest.stat().st_mtime
        if age_seconds > max_age_seconds:
            blockers.append(
                f"latest artifact is stale: age_seconds={age_seconds:.0f} max_age_seconds={max_age_seconds:.0f}"
            )
        blockers.extend(validate_artifact_shape(name, latest))
    return {
        "name": name,
        "artifact_kind": spec["artifact_kind"],
        "attach_argument": spec.get("attach_argument"),
        "ready": not blockers,
        "blockers": blockers,
        "candidate_count": len(candidates),
        "latest_artifact_path": str(latest) if latest else None,
        "latest_artifact_age_seconds": age_seconds,
    }


def excluded_candidate(path: Path, spec: dict[str, Any]) -> bool:
    name = path.name.lower()
    if any(part in name for part in spec.get("exclude_name_parts", ())):
        return True
    internal_parts = {".fingerprint", "deps", "incremental", "build"}
    return any(part in internal_parts for part in path.parts)


def validate_artifact_shape(name: str, path: Path) -> list[str]:
    if name == "benchmark_coverage":
        return validate_benchmark_jsonl(path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as error:  # noqa: BLE001 - inventory reports blocker
        return [f"artifact is not parseable JSON: {error}"]
    if not isinstance(payload, dict):
        return ["artifact payload is not a JSON object"]
    if name == "load_test_coverage":
        return validate_load_json(payload)
    if name == "load_comparison":
        return validate_load_comparison_json(payload)
    if name == "chaos_test_coverage":
        return validate_chaos_json(payload)
    if name == "rolling_upgrade_coverage":
        return validate_rolling_upgrade_json(payload)
    if name == "pit_e2e_coverage":
        return validate_pit_e2e_json(payload)
    if name == "promotion_gate_suite":
        return validate_promotion_gate_suite_json(payload)
    return validate_generic_json_evidence(payload)


def validate_benchmark_jsonl(path: Path) -> list[str]:
    records: list[Any] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(json.loads(line))
    except Exception as error:  # noqa: BLE001 - inventory reports blocker
        return [f"artifact is not parseable JSONL: {error}"]
    if not records:
        return ["benchmark JSONL contains no records"]
    if not any(isinstance(record, dict) and record.get("benchmark") for record in records):
        return ["benchmark JSONL contains no named benchmark records"]
    errors: list[str] = []
    names = {
        str(record.get("benchmark"))
        for record in records
        if isinstance(record, dict) and record.get("benchmark")
    }
    missing = sorted(REQUIRED_BENCHMARKS - names)
    if missing:
        errors.append(f"benchmark JSONL is missing expected records: {', '.join(missing)}")
    extra = sorted(names - REQUIRED_BENCHMARKS)
    if extra:
        errors.append(f"benchmark JSONL has unexpected records: {', '.join(extra)}")
    for record in records:
        if not isinstance(record, dict):
            errors.append("benchmark JSONL contains a non-object record")
            continue
        name = record.get("benchmark")
        for field in ("operations", "elapsed_nanos", "nanos_per_operation"):
            value = record.get(field)
            if not isinstance(value, int) or value <= 0:
                errors.append(f"{name}.{field} must be a positive integer")
    return errors


def validate_load_json(payload: dict[str, Any]) -> list[str]:
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        return ["load JSON summary is missing"]
    errors: list[str] = []
    if summary.get("passed") is not True:
        errors.append("load JSON summary.passed is not true")
    if summary.get("error_count", 0) != 0:
        errors.append(f"load JSON summary.error_count={summary.get('error_count')}")
    for field in ("operation_count", "success_count", "elapsed_seconds", "throughput_ops_per_second"):
        value = summary.get(field)
        if not isinstance(value, (int, float)) or value <= 0:
            errors.append(f"load JSON summary.{field} must be positive")
    if summary.get("error_rate") != 0.0:
        errors.append(f"load JSON summary.error_rate={summary.get('error_rate')}")
    operations = payload.get("operations")
    if not isinstance(operations, dict):
        errors.append("load JSON operations are missing")
    else:
        errors.extend(validate_load_operations(operations))
    resource_usage = payload.get("resource_usage")
    if not isinstance(resource_usage, dict):
        errors.append("load JSON resource_usage is missing")
    else:
        errors.extend(validate_load_resource_usage(resource_usage))
    return errors


def validate_load_operations(operations: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_LOAD_OPERATIONS - set(operations))
    if missing:
        errors.append(f"load JSON operations are missing: {', '.join(missing)}")
    for name in sorted(REQUIRED_LOAD_OPERATIONS & set(operations)):
        payload = operations.get(name)
        if not isinstance(payload, dict):
            errors.append(f"load JSON operation {name} is not an object")
            continue
        if payload.get("error_count") != 0:
            errors.append(f"load JSON operation {name}.error_count={payload.get('error_count')}")
        success_count = payload.get("success_count")
        if not isinstance(success_count, (int, float)) or success_count <= 0:
            errors.append(f"load JSON operation {name}.success_count must be positive")
        latency = payload.get("latency_ms")
        if not isinstance(latency, dict):
            errors.append(f"load JSON operation {name}.latency_ms is missing")
            continue
        for field in ("count", "p50", "p95", "p99", "mean", "max"):
            value = latency.get(field)
            if not isinstance(value, (int, float)) or value <= 0:
                errors.append(f"load JSON operation {name}.latency_ms.{field} must be positive")
    return errors


def validate_load_resource_usage(resource_usage: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_LOAD_RESOURCE_COUNTERS - set(resource_usage))
    if missing:
        errors.append(f"load JSON resource_usage counters are missing: {', '.join(missing)}")
    for name in sorted(REQUIRED_LOAD_RESOURCE_COUNTERS & set(resource_usage)):
        counter = resource_usage.get(name)
        if not isinstance(counter, dict):
            errors.append(f"load JSON resource_usage {name} is not an object")
            continue
        for field in ("before", "after", "delta"):
            value = counter.get(field)
            if not isinstance(value, (int, float)):
                errors.append(f"load JSON resource_usage {name}.{field} is missing")
        peak = counter.get("peak")
        if peak is not None and not isinstance(peak, (int, float)):
            errors.append(f"load JSON resource_usage {name}.peak must be numeric when present")
    return errors


def validate_load_comparison_json(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    targets = payload.get("targets")
    comparison = payload.get("comparison")
    if not isinstance(targets, dict):
        errors.append("load comparison targets are missing")
    else:
        for name in ("steelsearch", "opensearch"):
            target = targets.get(name)
            if not isinstance(target, dict):
                errors.append(f"load comparison target is missing: {name}")
            elif target.get("returncode", 0) != 0:
                errors.append(f"load comparison {name}.returncode={target.get('returncode')}")
    if not isinstance(comparison, dict):
        errors.append("load comparison comparison object is missing")
    elif comparison.get("mode") == "dry-run":
        errors.append("load comparison is a dry-run report")
    return errors


def validate_chaos_json(payload: dict[str, Any]) -> list[str]:
    errors = validate_generic_json_evidence(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("chaos summary is missing")
    elif summary.get("coverage_scope") != "mixed-cluster failure fixture":
        errors.append("chaos coverage_scope mismatch")
    source = payload.get("source_report")
    if not isinstance(source, dict):
        errors.append("chaos source_report is missing")
    elif source.get("summary", {}).get("passed") is not True:
        errors.append("chaos source_report summary.passed is not true")
    else:
        errors.extend(validate_chaos_source_checks(source))
    return errors


def validate_chaos_source_checks(source: dict[str, Any]) -> list[str]:
    checks = source.get("checks")
    if not isinstance(checks, dict):
        return ["chaos source_report checks are missing"]
    expected = {
        "failure_topology_probe_passed",
        "failure_ledger_passed",
        "pit_restart_lifecycle_passed",
        "pit_transport_restart_lifecycle_passed",
        "pit_multi_daemon_lifecycle_passed",
    }
    errors: list[str] = []
    missing = sorted(expected - set(checks))
    if missing:
        errors.append(f"chaos source_report checks are missing: {', '.join(missing)}")
    for name in sorted(expected & set(checks)):
        if checks.get(name) is not True:
            errors.append(f"chaos source_report check is not true: {name}")
    executed_tests = source.get("executed_tests")
    expected_tests = {
        "daemon_point_in_time_contexts_do_not_survive_restart",
        "daemon_transport_point_in_time_contexts_do_not_survive_restart",
        "multi_daemon_get_all_pits_fans_out_to_seed_peers",
    }
    if not isinstance(executed_tests, list):
        errors.append("chaos source_report executed_tests are missing")
    else:
        missing_tests = sorted(expected_tests - {str(test) for test in executed_tests})
        if missing_tests:
            errors.append(
                f"chaos source_report executed_tests are missing: {', '.join(missing_tests)}"
            )
    errors.extend(validate_chaos_child_executed_tests(source))
    return errors


def validate_chaos_child_executed_tests(source: dict[str, Any]) -> list[str]:
    child_executed_tests = source.get("child_executed_tests")
    expected_child_tests = {
        "pit_restart_lifecycle_report": {
            "daemon_point_in_time_contexts_do_not_survive_restart",
        },
        "pit_transport_restart_lifecycle_report": {
            "daemon_transport_point_in_time_contexts_do_not_survive_restart",
        },
        "pit_multi_daemon_lifecycle_report": {
            "multi_daemon_get_all_pits_fans_out_to_seed_peers",
        },
    }
    if not isinstance(child_executed_tests, dict):
        return ["chaos source_report child_executed_tests are missing"]
    errors: list[str] = []
    child_union: set[str] = set()
    for child_name, required_tests in sorted(expected_child_tests.items()):
        child_tests = child_executed_tests.get(child_name)
        if not isinstance(child_tests, list):
            errors.append(f"chaos source_report child_executed_tests are missing: {child_name}")
            continue
        child_test_names = {str(test) for test in child_tests}
        child_union.update(child_test_names)
        missing_tests = sorted(required_tests - child_test_names)
        if missing_tests:
            errors.append(
                f"chaos source_report {child_name} executed_tests are missing: {', '.join(missing_tests)}"
            )
    final_tests = source.get("executed_tests")
    if isinstance(final_tests, list) and child_union != {str(test) for test in final_tests}:
        errors.append("chaos source_report executed_tests do not match child_executed_tests")
    return errors


def validate_rolling_upgrade_json(payload: dict[str, Any]) -> list[str]:
    errors = validate_generic_json_evidence(payload)
    summary = payload.get("summary")
    if not isinstance(summary, dict):
        errors.append("rolling-upgrade summary is missing")
    else:
        if summary.get("coverage_scope") != "rolling-upgrade transcript fixture":
            errors.append("rolling-upgrade coverage_scope mismatch")
        if summary.get("passed") is not True:
            errors.append("rolling-upgrade summary.passed is not true")
        if summary.get("step_count") != len(REQUIRED_ROLLING_UPGRADE_STEPS):
            errors.append("rolling-upgrade summary.step_count mismatch")
        if summary.get("transcript_step_count") != len(REQUIRED_ROLLING_UPGRADE_STEPS):
            errors.append("rolling-upgrade summary.transcript_step_count mismatch")
    transcript = payload.get("transcript")
    if not isinstance(transcript, dict):
        errors.append("rolling-upgrade transcript is missing")
    else:
        if transcript.get("profile") != "rolling-upgrade":
            errors.append("rolling-upgrade transcript profile mismatch")
        if transcript.get("status") != "completed":
            errors.append(f"rolling-upgrade transcript status mismatch: {transcript.get('status')}")
        if transcript.get("steps") != REQUIRED_ROLLING_UPGRADE_STEPS:
            errors.append("rolling-upgrade transcript steps mismatch")
        if transcript.get("transcript") != REQUIRED_ROLLING_UPGRADE_STEPS:
            errors.append("rolling-upgrade transcript execution order mismatch")
        if transcript.get("transcript_assertions") != REQUIRED_ROLLING_UPGRADE_ASSERTIONS:
            errors.append("rolling-upgrade transcript assertions mismatch")
    assertion_hits = payload.get("assertion_hits")
    if not isinstance(assertion_hits, dict) or not assertion_hits:
        errors.append("rolling-upgrade assertion_hits is missing")
    else:
        missing = sorted(set(REQUIRED_ROLLING_UPGRADE_ASSERTIONS) - set(assertion_hits))
        if missing:
            errors.append(f"rolling-upgrade assertion_hits missing: {', '.join(missing)}")
        failed = sorted(name for name, passed in assertion_hits.items() if passed is not True)
        if failed:
            errors.append(f"rolling-upgrade assertion_hits failed: {', '.join(failed)}")
    return errors


def validate_pit_e2e_json(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("status") not in {"ok", "missing"}:
        errors.append(f"PIT E2E report status mismatch: {payload.get('status')}")
    suite_results = payload.get("suite_results") or payload.get("suites")
    if not isinstance(suite_results, list) or not suite_results:
        return errors + ["PIT E2E suite_results are missing"]
    suites = {
        suite.get("name"): suite
        for suite in suite_results
        if isinstance(suite, dict) and suite.get("name") in REQUIRED_PIT_CASES
    }
    for suite_name, required_cases in sorted(REQUIRED_PIT_CASES.items()):
        suite = suites.get(suite_name)
        if suite is None:
            errors.append(f"PIT E2E suite is missing: {suite_name}")
            continue
        if suite.get("has_opensearch_target") is not True:
            errors.append(f"PIT E2E suite is not OpenSearch-compared: {suite_name}")
        passed_cases = suite.get("passed_cases")
        case_gaps = suite.get("case_gaps")
        if not isinstance(passed_cases, list) or not isinstance(case_gaps, dict):
            errors.append(f"PIT E2E suite lacks embedded case evidence: {suite_name}")
            continue
        passed_case_names = {str(case) for case in passed_cases}
        missing = sorted(required_cases - passed_case_names)
        if missing:
            errors.append(
                f"PIT E2E suite missing passed required cases [{suite_name}]: {', '.join(missing)}"
            )
        for gap_name in ("failed", "skipped", "missing"):
            gap_cases = case_gaps.get(gap_name)
            if not isinstance(gap_cases, list):
                continue
            required_gap_cases = sorted(required_cases & {str(case) for case in gap_cases})
            if required_gap_cases:
                errors.append(
                    f"PIT E2E suite has {gap_name} required cases [{suite_name}]: {', '.join(required_gap_cases)}"
                )
    return errors


def validate_promotion_gate_suite_json(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if payload.get("status") != "ok":
        errors.append(f"promotion gate suite status mismatch: {payload.get('status')}")
    if payload.get("failed") != 0:
        errors.append(f"promotion gate suite failed={payload.get('failed')}")
    checks = payload.get("checks")
    if not isinstance(checks, list) or not checks:
        errors.append("promotion gate suite checks are missing")
        return errors
    if payload.get("passed") != len(checks):
        errors.append("promotion gate suite passed count does not match checks")
    check_names = {
        str(check.get("name"))
        for check in checks
        if isinstance(check, dict) and check.get("name")
    }
    missing_checks = sorted(REQUIRED_PROMOTION_GATE_CHECKS - check_names)
    if missing_checks:
        errors.append(
            "promotion gate suite missing required checks: "
            f"{', '.join(missing_checks)}"
        )
    extra_checks = sorted(
        check_names - REQUIRED_PROMOTION_GATE_CHECKS - OPTIONAL_PROMOTION_GATE_CHECKS
    )
    if extra_checks:
        errors.append(
            "promotion gate suite has unexpected checks: "
            f"{', '.join(extra_checks)}"
        )
    failed_checks = sorted(
        str(check.get("name") or index)
        for index, check in enumerate(checks)
        if not isinstance(check, dict)
        or check.get("status") != "ok"
        or check.get("returncode") != 0
    )
    if failed_checks:
        errors.append(f"promotion gate suite has failed checks: {', '.join(failed_checks)}")
    checks_by_name = {
        str(check.get("name")): check
        for check in checks
        if isinstance(check, dict) and check.get("name")
    }
    for name, fragments in sorted(REQUIRED_PROMOTION_GATE_COMMAND_FRAGMENTS.items()):
        check = checks_by_name.get(name)
        if check is None:
            continue
        command = str(check.get("command") or "")
        missing_fragments = [fragment for fragment in fragments if fragment not in command]
        if missing_fragments:
            errors.append(
                f"promotion gate suite check [{name}] command missing required fragment(s): "
                f"{', '.join(missing_fragments)}"
            )
    return errors


def validate_generic_json_evidence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    summary = payload.get("summary")
    if isinstance(summary, dict) and summary.get("error_count", 0) != 0:
        errors.append(f"evidence summary.error_count={summary.get('error_count')}")
    blockers = payload.get("blockers")
    if isinstance(blockers, list) and blockers:
        errors.append("evidence blockers is not empty")
    if payload.get("ready") is False or payload.get("passed") is False:
        errors.append("evidence reports ready/passed false")
    return errors


def unique_paths(paths: Any) -> list[Path]:
    seen: set[Path] = set()
    result: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(path)
    return result


def attach_command_template(items: dict[str, dict[str, Any]]) -> list[str]:
    command = [
        "python3",
        "tools/attach-release-readiness-evidence.py",
        "--readiness-report",
        "<readiness-report.json>",
    ]
    ordered = [
        "benchmark_coverage",
        "load_test_coverage",
        "load_comparison",
        "chaos_test_coverage",
        "packaging_verified",
        "rolling_upgrade_coverage",
    ]
    for name in ordered:
        item = items[name]
        command.extend(
            [
                item["attach_argument"],
                item["latest_artifact_path"] or f"<{name}>",
            ]
        )
        if name == "benchmark_coverage":
            command.extend(
                [
                    "--benchmark-comparison-summary",
                    "target/search-benchmark-matrix-current-20260630T023334Z/summary.json",
                ]
            )
    command.extend(["--release-readiness-file", "<release-readiness.json>"])
    return command


if __name__ == "__main__":
    raise SystemExit(main())
