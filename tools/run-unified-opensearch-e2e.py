#!/usr/bin/env python3
"""Run or collect broad Steelsearch/OpenSearch E2E compatibility reports."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = ROOT / "target" / "unified-opensearch-e2e"


@dataclass(frozen=True)
class Suite:
    name: str
    area: str
    parity_section: str
    runner: str | None
    fixture: str
    report: str
    required: bool = True


SUITES: tuple[Suite, ...] = (
    Suite("root-cluster-node", "root-cluster-node", "route_parity", "tools/root_cluster_node_compat.py", "tools/fixtures/root-cluster-node-compat.json", "root-cluster-node-compat-report.json"),
    Suite("cluster-health", "cluster-admin", "route_parity", "tools/cluster_health_compat.py", "tools/fixtures/cluster-health-compat.json", "cluster-health-compat-report.json"),
    Suite("allocation-explain", "cluster-admin", "route_parity", "tools/allocation_explain_compat.py", "tools/fixtures/allocation-explain-compat.json", "allocation-explain-compat-report.json"),
    Suite("cluster-state", "cluster-admin", "route_parity", "tools/cluster_state_compat.py", "tools/fixtures/cluster-state-compat.json", "cluster-state-compat-report.json"),
    Suite("tasks", "tasks", "route_parity", "tools/tasks_compat.py", "tools/fixtures/tasks-compat.json", "tasks-compat-report.json"),
    Suite("stats", "stats", "route_parity", "tools/stats_compat.py", "tools/fixtures/stats-compat.json", "stats-compat-report.json"),
    Suite("index-lifecycle", "index-metadata", "route_parity", "tools/index_lifecycle_compat.py", "tools/fixtures/index-lifecycle-compat.json", "index-lifecycle-compat-report.json"),
    Suite("mapping", "index-metadata", "route_parity", "tools/mapping_compat.py", "tools/fixtures/mapping-compat.json", "mapping-compat-report.json"),
    Suite("settings", "index-metadata", "route_parity", "tools/settings_compat.py", "tools/fixtures/settings-compat.json", "settings-compat-report.json"),
    Suite("alias-read", "index-metadata", "route_parity", "tools/alias_read_compat.py", "tools/fixtures/alias-read-compat.json", "alias-read-compat-report.json"),
    Suite("template", "index-metadata", "route_parity", "tools/template_compat.py", "tools/fixtures/template-compat.json", "template-compat-report.json"),
    Suite("data-stream-rollover", "index-metadata", "route_parity", "tools/data_stream_rollover_compat.py", "tools/fixtures/data-stream-rollover-compat.json", "data-stream-rollover-compat-report.json"),
    Suite("single-doc-crud", "document-write", "semantic_parity", "tools/single_doc_crud_compat.py", "tools/fixtures/single-doc-crud-compat.json", "single-doc-crud-compat-report.json"),
    Suite("refresh", "document-write", "semantic_parity", "tools/refresh_compat.py", "tools/fixtures/refresh-compat.json", "refresh-compat-report.json"),
    Suite("routing", "document-write", "semantic_parity", "tools/routing_compat.py", "tools/fixtures/routing-compat.json", "routing-compat-report.json"),
    Suite("bulk", "document-write", "semantic_parity", "tools/bulk_compat.py", "tools/fixtures/bulk-compat.json", "bulk-compat-report.json"),
    Suite("search-compat", "search", "semantic_parity", "tools/search_compat.py", "tools/fixtures/search-compat.json", "search-compat-report.json"),
    Suite("search-strict", "search", "semantic_parity", "tools/search_compat.py", "tools/fixtures/search-strict-compat.json", "search-strict-compat-report.json"),
    Suite("search-semantic", "search", "semantic_parity", "tools/search_compat.py", "tools/fixtures/search-semantic-compat.json", "search-semantic-compat-report.json"),
    Suite("vector-search", "vector-ml", "semantic_parity", "tools/vector_search_compat.py", "tools/fixtures/vector-search-compat.json", "vector-search-compat-report.json"),
    Suite("ml-model-surface", "vector-ml", "semantic_parity", "tools/ml_model_surface_compat.py", "tools/fixtures/ml-model-surface-compat.json", "ml-model-surface-compat-report.json"),
    Suite("snapshot-lifecycle", "snapshot", "durability_parity", "tools/snapshot_lifecycle_compat.py", "tools/fixtures/snapshot-lifecycle-compat.json", "snapshot-lifecycle-compat-report.json"),
    Suite("alias-template-persistence", "durability", "durability_parity", "tools/alias_template_persistence_compat.py", "tools/fixtures/alias-template-persistence-compat.json", "alias-template-persistence-report.json"),
    Suite("security-authz", "security", "security_parity", None, "tools/fixtures/security-authz-compat.json", "security-authz-compat-report.json", required=False),
    Suite("multi-node-write-path", "distributed", "distributed_parity", None, "tools/fixtures/comparison-harness-required-suites.json", "multi-node-write-path-report.json", required=False),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--profile", default="broad-opensearch-e2e")
    parser.add_argument("--steelsearch-url")
    parser.add_argument("--opensearch-url")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--run", action="store_true", help="run live suites instead of only collecting existing reports")
    parser.add_argument("--suite", action="append", help="suite name to include; may be repeated")
    parser.add_argument("--allow-missing", action="store_true", help="exit 0 even if required suite reports are missing")
    parser.add_argument(
        "--no-recursive-target-scan",
        action="store_true",
        help="only collect reports from output-dir and target/<report>, not target/**/<report>",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    suites = select_suites(args.suite)

    suite_results = []
    if args.run:
        if not args.steelsearch_url or not args.opensearch_url:
            raise SystemExit("--run requires --steelsearch-url and --opensearch-url")
        for suite in suites:
            suite_results.append(run_or_collect_suite(suite, output_dir, args))
    else:
        for suite in suites:
            suite_results.append(collect_suite(suite, output_dir, recursive_target_scan=not args.no_recursive_target_scan))

    report = build_report(args.profile, suite_results)
    report_path = output_dir / "unified-opensearch-e2e-report.json"
    markdown_path = output_dir / "unified-opensearch-e2e-report.md"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.write_text(render_markdown(report), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if report["status"] != "ok" and not args.allow_missing:
        return 1
    return 0


def select_suites(names: list[str] | None) -> tuple[Suite, ...]:
    if not names:
        return SUITES
    by_name = {suite.name: suite for suite in SUITES}
    missing = sorted(set(names) - set(by_name))
    if missing:
        raise SystemExit(f"unknown suite(s): {', '.join(missing)}")
    return tuple(by_name[name] for name in names)


def run_or_collect_suite(suite: Suite, output_dir: Path, args: argparse.Namespace) -> dict[str, Any]:
    report_path = output_dir / suite.report
    if suite.runner is None:
        return collect_suite(suite, output_dir, note="no live runner is registered for this suite")
    command = [
        sys.executable,
        str(ROOT / suite.runner),
        "--steelsearch-url",
        args.steelsearch_url.rstrip("/"),
        "--opensearch-url",
        args.opensearch_url.rstrip("/"),
        "--fixture",
        str(ROOT / suite.fixture),
        "--output",
        str(report_path),
        "--timeout",
        str(args.timeout),
    ]
    started = time.time()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    result = collect_suite(suite, output_dir)
    result["run"] = {
        "command": command,
        "duration_seconds": time.time() - started,
        "returncode": completed.returncode,
        "stdout_tail": completed.stdout[-4000:],
        "stderr_tail": completed.stderr[-4000:],
    }
    if completed.returncode != 0 and result["status"] == "missing":
        result["status"] = "failed"
    return result


def collect_suite(
    suite: Suite,
    output_dir: Path,
    note: str | None = None,
    recursive_target_scan: bool = True,
) -> dict[str, Any]:
    fixture_path = ROOT / suite.fixture
    fixture = load_json(fixture_path)
    report_path = output_dir / suite.report
    source = "output-dir"
    if not report_path.exists():
        target_report = ROOT / "target" / suite.report
        if target_report.exists():
            report_path = target_report
            source = "target"
    if not report_path.exists() and recursive_target_scan:
        recursive_report = newest_target_report(suite.report)
        if recursive_report is not None:
            report_path = recursive_report
            source = "target-recursive"
    report = load_json(report_path) if report_path.exists() else None
    result = summarize_suite(suite, fixture, report)
    result["fixture_path"] = str(fixture_path)
    result["report_path"] = str(report_path) if report_path.exists() else str(output_dir / suite.report)
    result["report_source"] = source if report is not None else "missing"
    if note:
        result["note"] = note
    return result


def newest_target_report(report_name: str) -> Path | None:
    candidates = [
        path for path in (ROOT / "target").glob(f"**/{report_name}")
        if path.is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_suite(suite: Suite, fixture: dict[str, Any], report: dict[str, Any] | None) -> dict[str, Any]:
    fixture_cases = fixture.get("cases") or []
    base = {
        "name": suite.name,
        "area": suite.area,
        "parity_section": suite.parity_section,
        "required": suite.required,
        "fixture_case_count": len(fixture_cases),
    }
    if report is None:
        return {
            **base,
            "status": "missing" if suite.required else "blocked",
            "summary": {"passed": 0, "failed": 0, "skipped": 0},
            "has_opensearch_target": False,
            "classification": empty_classification(),
            "by_area": {},
        }
    summary = report.get("summary") or {}
    failed = int(summary.get("failed") or 0)
    skipped = int(summary.get("skipped") or 0)
    status = "ok" if failed == 0 else "failed"
    if skipped and failed == 0:
        status = "ok"
    has_opensearch = "opensearch" in (report.get("targets") or {})
    classification = classify_cases(fixture_cases, report.get("cases") or [], has_opensearch)
    return {
        **base,
        "status": status,
        "summary": {
            "passed": int(summary.get("passed") or 0),
            "failed": failed,
            "skipped": skipped,
        },
        "has_opensearch_target": has_opensearch,
        "classification": classification,
        "by_area": summary.get("by_area") or {},
    }


def empty_classification() -> dict[str, int]:
    return {
        "strict_equal": 0,
        "canonical_equal": 0,
        "semantic_equal": 0,
        "steelsearch_fail_closed": 0,
        "steelsearch_only": 0,
        "known_gap_or_skipped": 0,
        "failed": 0,
        "missing": 0,
    }


def classify_cases(fixture_cases: list[dict[str, Any]], report_cases: list[dict[str, Any]], has_opensearch: bool) -> dict[str, int]:
    counts = empty_classification()
    fixture_by_name = {case.get("name"): case for case in fixture_cases}
    report_by_name = {case.get("name"): case for case in report_cases}
    for name, fixture_case in fixture_by_name.items():
        report_case = report_by_name.get(name)
        if report_case is None:
            counts["missing"] += 1
            continue
        status = report_case.get("status")
        if status == "failed":
            counts["failed"] += 1
            continue
        if status == "skipped":
            counts["known_gap_or_skipped"] += 1
            continue
        if fixture_case.get("comparison") == "steelsearch_only":
            if "expected_steelsearch_status" in fixture_case:
                counts["steelsearch_fail_closed"] += 1
            else:
                counts["steelsearch_only"] += 1
            continue
        if not has_opensearch:
            counts["steelsearch_only"] += 1
        elif fixture_case.get("strict_source_parity_required") is True:
            counts["strict_equal"] += 1
        elif fixture_case.get("expect_hits") is not None or fixture_case.get("expected_steelsearch_status") is not None:
            counts["semantic_equal"] += 1
        else:
            counts["canonical_equal"] += 1
    extra = set(report_by_name) - set(fixture_by_name)
    counts["missing"] += len(extra)
    return counts


def build_report(profile: str, suite_results: list[dict[str, Any]]) -> dict[str, Any]:
    sections = {
        name: section_summary(name, suite_results)
        for name in ("route_parity", "semantic_parity", "durability_parity", "security_parity", "distributed_parity")
    }
    status = "ok"
    if any(section["status"] == "missing" for section in sections.values()):
        status = "missing"
    if any(section["status"] == "blocked" for section in sections.values()):
        status = "blocked"
    totals = empty_classification()
    for suite in suite_results:
        for key, value in suite["classification"].items():
            totals[key] += int(value)
    return {
        "profile": profile,
        "generated_at": int(time.time()),
        "status": status,
        **sections,
        "coverage_summary": {
            "suite_count": len(suite_results),
            "required_suite_count": sum(1 for suite in suite_results if suite["required"]),
            "reported_suite_count": sum(1 for suite in suite_results if suite["report_source"] != "missing"),
            "opensearch_compared_suite_count": sum(1 for suite in suite_results if suite["has_opensearch_target"]),
            "case_classification": totals,
        },
        "suite_results": suite_results,
    }


def section_summary(section_name: str, suite_results: list[dict[str, Any]]) -> dict[str, Any]:
    suites = [suite for suite in suite_results if suite["parity_section"] == section_name]
    required = [suite for suite in suites if suite["required"]]
    missing = [suite for suite in required if suite["report_source"] == "missing"]
    failed = [suite for suite in required if suite["summary"]["failed"]]
    status = "ok"
    if failed:
        status = "blocked"
    elif missing:
        status = "missing"
    return {
        "required_suites": [suite["name"] for suite in required],
        "report_paths": [suite["report_path"] for suite in suites if suite["report_source"] != "missing"],
        "status": status,
        "missing_suites": [suite["name"] for suite in missing],
        "failed_suites": [suite["name"] for suite in failed],
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Unified OpenSearch E2E Comparison Report",
        "",
        f"- Profile: `{report['profile']}`",
        f"- Status: `{report['status']}`",
        f"- Suites with reports: `{report['coverage_summary']['reported_suite_count']}/{report['coverage_summary']['suite_count']}`",
        f"- Suites with OpenSearch target: `{report['coverage_summary']['opensearch_compared_suite_count']}`",
        "",
        "## Suite Summary",
        "",
        "| Suite | Section | Required | Status | OpenSearch target | Passed | Failed | Skipped |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: |",
    ]
    for suite in report["suite_results"]:
        summary = suite["summary"]
        lines.append(
            f"| {suite['name']} | {suite['parity_section']} | {str(suite['required']).lower()} | {suite['status']} | {str(suite['has_opensearch_target']).lower()} | {summary['passed']} | {summary['failed']} | {summary['skipped']} |"
        )
    lines.extend(["", "## Classification", "", "| Class | Cases |", "| --- | ---: |"])
    for key, value in report["coverage_summary"]["case_classification"].items():
        lines.append(f"| {key} | {value} |")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
