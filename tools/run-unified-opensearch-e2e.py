#!/usr/bin/env python3
"""Run or collect broad Steelsearch/OpenSearch E2E compatibility reports."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


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
    output_arg: str = "--output"
    needs_opensearch: bool = True
    accepts_optional_opensearch: bool = False
    allow_partial_report: bool = False
    default_cases: tuple[str, ...] = ()
    runner_kind: str = "compat"
    report_aliases: tuple[str, ...] = ()


ROOT_CLUSTER_NODE_CAT_COMMON_CASES: tuple[str, ...] = (
    "cat_root_text",
    "dangling_indices_shape",
    "settings_named_global_shape",
    "settings_named_target_shape",
    "setting_named_target_shape",
    "index_stats_metric_shape",
    "index_stats_target_shape",
    "index_stats_target_metric_shape",
    "analyze_global_get_tokens",
    "analyze_target_get_tokens",
    "flush_global_shape",
    "flush_target_shape",
    "resolve_index_shape",
    "shard_stores_global_shape",
    "shard_stores_target_shape",
    "upgrade_global_shape",
    "upgrade_target_shape",
    "ingestion_state_shape",
    "cat_allocation_text",
    "cat_fielddata_text",
    "cat_pending_tasks_text",
    "cat_pit_segments_error",
    "cat_pit_segments_all_text",
    "cat_recovery_text",
    "cat_recovery_target_text",
    "cat_repositories_text",
    "cat_snapshots_error",
    "cat_tasks_text",
    "cat_templates_text",
    "cat_templates_target_text",
    "cat_thread_pool_text",
    "cat_thread_pool_target_text",
    "decommission_awareness_status",
    "cluster_stats_nodes_all_shape",
    "cluster_stats_metric_nodes_shape",
    "cluster_stats_metric_index_metric_nodes_shape",
    "nodes_hot_threads_text",
    "nodes_hot_threads_target_text",
    "nodes_hotthreads_deprecated_alias_text",
    "nodes_target_hotthreads_deprecated_alias_text",
    "cluster_nodes_hot_threads_deprecated_alias_text",
    "cluster_nodes_target_hot_threads_deprecated_alias_text",
    "cluster_nodes_hotthreads_deprecated_alias_text",
    "cluster_nodes_target_hotthreads_deprecated_alias_text",
    "nodes_stats_metric_shape",
    "nodes_stats_metric_index_metric_shape",
    "nodes_stats_target_shape",
    "nodes_stats_target_metric_shape",
    "nodes_stats_target_metric_index_metric_shape",
    "nodes_usage_shape",
    "nodes_usage_metric_shape",
    "nodes_usage_unknown_metric_shape",
    "nodes_usage_target_shape",
    "nodes_usage_target_metric_shape",
    "nodes_info_root_shape",
    "remote_info_shape",
    "remote_store_metadata_missing_index",
    "snapshot_index_status_missing_repository",
    "nodes_info_shape",
    "nodes_info_metric_shape",
    "nodes_info_metric_shorthand_shape",
    "nodes_info_ignores_unknown_metric_shape",
    "nodes_info_info_metric_shape",
    "search_shards_global_get_shape",
    "search_shards_target_get_shape",
    "script_context_shape",
    "script_language_shape",
    "cat_shards_json",
    "cat_shards_text",
    "cat_segments_json",
    "cat_segments_text",
    "remote_store_stats_missing_index",
    "allocation_explain_get_error",
)


ADMIN_OPS_COMMON_CASES: tuple[str, ...] = (
    "admin_ops_scroll_root_get_semantic",
    "admin_ops_scroll_named_delete_semantic",
    "admin_ops_pit_list_semantic",
    "admin_ops_pit_delete_all_semantic",
    "admin_ops_close_repeat_semantic",
    "admin_ops_open_repeat_semantic",
    "admin_ops_tier_default_no_handler_semantic",
    "admin_ops_flush_selector_semantic",
    "admin_ops_refresh_selector_semantic",
    "admin_ops_cache_clear_selector_semantic",
    "admin_ops_forcemerge_selector_semantic",
    "admin_ops_tasks_cancel_non_cancellable_semantic",
    "admin_ops_tasks_cancel_unknown_semantic",
    "admin_ops_reindex_rethrottle_known_semantic",
    "admin_ops_reindex_rethrottle_unknown_semantic",
)


SUITES: tuple[Suite, ...] = (
    Suite("root-cluster-node", "root-cluster-node", "route_parity", "tools/root_cluster_node_compat.py", "tools/fixtures/root-cluster-node-compat.json", "root-cluster-node-compat-report.json"),
    Suite(
        "root-cluster-node-cat-common",
        "root-cluster-node",
        "route_parity",
        "tools/root_cluster_node_compat.py",
        "tools/fixtures/root-cluster-node-cat-compat.json",
        "root-cluster-node-cat-common-compat-report.json",
        allow_partial_report=True,
        default_cases=ROOT_CLUSTER_NODE_CAT_COMMON_CASES,
    ),
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
    Suite("document-write-semantic", "document-write", "semantic_parity", "tools/search_compat.py", "tools/fixtures/document-write-semantic-compat.json", "document-write-semantic-compat-report.json", output_arg="--report"),
    Suite("search-compat", "search", "semantic_parity", "tools/search_compat.py", "tools/fixtures/search-compat.json", "search-compat-report.json", output_arg="--report"),
    Suite(
        "search-strict",
        "search",
        "semantic_parity",
        "tools/search_compat.py",
        "tools/fixtures/search-strict-compat.json",
        "search-strict-compat-report.json",
        output_arg="--report",
        report_aliases=("quoted-phrase-report.json", "query-string-family-report.json"),
    ),
    Suite("search-semantic", "search", "semantic_parity", "tools/search_compat.py", "tools/fixtures/search-semantic-compat.json", "search-semantic-compat-report.json", output_arg="--report"),
    Suite("runtime-stateful-probe", "runtime-stateful", "semantic_parity", "tools/probe_stateful_route_ledger.py", "tools/fixtures/runtime-stateful-probe.json", "runtime-stateful-probe-report.json", output_arg="--report", needs_opensearch=True),
    Suite(
        "admin-ops-common",
        "admin-ops",
        "semantic_parity",
        "tools/search_compat.py",
        "tools/fixtures/admin-ops-semantic-compat.json",
        "admin-ops-common-report.json",
        output_arg="--report",
        allow_partial_report=True,
        default_cases=ADMIN_OPS_COMMON_CASES,
    ),
    Suite("vector-search", "vector-ml", "semantic_parity", "tools/vector_search_compat.py", "tools/fixtures/vector-search-compat.json", "vector-search-compat-report.json"),
    Suite(
        "vector-search-native-surface",
        "vector-ml",
        "semantic_parity",
        "tools/vector_search_compat.py",
        "tools/fixtures/vector-search-compat.json",
        "vector-search-native-surface-report.json",
        needs_opensearch=False,
        accepts_optional_opensearch=True,
    ),
    Suite(
        "knn-plugin-surface",
        "vector-ml",
        "semantic_parity",
        "tools/search_compat.py",
        "tools/fixtures/search-compat.json",
        "knn-plugin-compat-report.json",
        output_arg="--report",
        needs_opensearch=False,
        accepts_optional_opensearch=True,
        allow_partial_report=True,
        default_cases=(
            "knn_settings_readback",
            "knn_warmup_basic_shape",
            "knn_clear_cache_basic_shape",
            "knn_model_lifecycle_shape",
            "knn_warmup_post_method_not_allowed",
            "knn_warmup_clear_cache_telemetry_shape",
            "knn_faiss_method_engine_search",
            "knn_on_disk_mode_search",
        ),
    ),
    Suite(
        "tier-read-surface",
        "index-metadata",
        "route_parity",
        "tools/search_compat.py",
        "tools/fixtures/search-compat.json",
        "tier-read-surface-report.json",
        output_arg="--report",
        allow_partial_report=True,
        default_cases=(
            "tier_all_shape",
            "tier_index_shape",
        ),
    ),
    Suite(
        "runtime-mappings-surface",
        "search",
        "semantic_parity",
        "tools/search_compat.py",
        "tools/fixtures/search-compat.json",
        "runtime-mappings-surface-report.json",
        output_arg="--report",
        allow_partial_report=True,
        default_cases=(
            "runtime_mappings_field_request_search",
            "runtime_mappings_string_script_search",
        ),
    ),
    Suite(
        "ml-model-surface",
        "vector-ml",
        "semantic_parity",
        "tools/ml_model_surface_compat.py",
        "tools/fixtures/ml-model-surface-compat.json",
        "ml-model-surface-compat-report.json",
        needs_opensearch=False,
        accepts_optional_opensearch=True,
    ),
    Suite("snapshot-lifecycle", "snapshot", "durability_parity", "tools/snapshot_lifecycle_compat.py", "tools/fixtures/snapshot-lifecycle-compat.json", "snapshot-lifecycle-compat-report.json"),
    Suite("alias-template-persistence", "durability", "durability_parity", "tools/alias_template_persistence_compat.py", "tools/fixtures/alias-template-persistence-compat.json", "alias-template-persistence-report.json"),
    Suite(
        "security-authz",
        "security",
        "security_parity",
        "tools/run-security-compat-harness.sh",
        "tools/fixtures/security-authz-compat.json",
        "security-authz-compat-report.json",
        needs_opensearch=False,
        accepts_optional_opensearch=True,
        output_arg="--report",
        runner_kind="security-harness",
    ),
    Suite(
        "multi-node-transport-admin",
        "distributed",
        "distributed_parity",
        "tools/multi_node_transport_admin_integration.py",
        "tools/fixtures/multi-node-transport-admin.json",
        "multi-node-transport-admin-report.json",
        needs_opensearch=False,
        accepts_optional_opensearch=True,
        output_arg="--output",
        runner_kind="multi-node",
    ),
    Suite(
        "multi-node-write-path",
        "distributed",
        "distributed_parity",
        "tools/multi_node_write_path_integration.py",
        "tools/fixtures/multi-node-write-path.json",
        "multi-node-write-path-report.json",
        required=False,
        needs_opensearch=False,
        output_arg="--output",
        runner_kind="multi-node",
    ),
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--profile", default="broad-opensearch-e2e")
    parser.add_argument("--steelsearch-url")
    parser.add_argument("--opensearch-url")
    parser.add_argument("--node-a-url")
    parser.add_argument("--node-b-url")
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--run", action="store_true", help="run live suites instead of only collecting existing reports")
    parser.add_argument("--suite", action="append", help="suite name to include; may be repeated")
    parser.add_argument("--case", action="append", help="case name to run; may be repeated")
    parser.add_argument("--allow-missing", action="store_true", help="exit 0 even if required suite reports are missing")
    parser.add_argument(
        "--max-report-age-seconds",
        type=float,
        help="ignore collected suite reports older than this many seconds",
    )
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
        if not args.steelsearch_url and not args.node_a_url:
            raise SystemExit("--run requires --steelsearch-url or --node-a-url")
        if any(suite.needs_opensearch for suite in suites) and not args.opensearch_url:
            raise SystemExit("--run requires --opensearch-url for selected OpenSearch comparison suites")
        for suite in suites:
            suite_results.append(run_or_collect_suite(suite, output_dir, args))
    else:
        report_index = (
            build_target_report_index(suites)
            if not args.no_recursive_target_scan
            else None
        )
        for suite in suites:
            suite_results.append(
                collect_suite(
                    suite,
                    output_dir,
                    recursive_target_scan=not args.no_recursive_target_scan,
                    max_report_age_seconds=args.max_report_age_seconds,
                    require_opensearch_target=(
                        suite.needs_opensearch
                        or (suite.accepts_optional_opensearch and bool(args.opensearch_url))
                    ),
                    report_index=report_index,
                )
            )

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
    fixture = load_json(ROOT / suite.fixture)
    fixture_case_names = {
        str(case.get("name"))
        for case in fixture.get("cases") or []
        if isinstance(case, dict) and case.get("name")
    }
    expected_case_names = set(suite.default_cases) if suite.default_cases else fixture_case_names
    baseline_report = None
    if args.case:
        _, _, baseline_report, _ = load_best_report(
            suite.report,
            ROOT / suite.fixture,
            output_dir,
            recursive_target_scan=not args.no_recursive_target_scan,
            exclude_paths={report_path.resolve()},
            max_report_age_seconds=args.max_report_age_seconds,
            expected_case_names=expected_case_names,
        )
    command = suite_run_command(suite, output_dir, args, report_path)
    selected_cases = args.case or list(suite.default_cases)
    if suite_supports_case_filter(suite):
        for case_name in selected_cases:
            command.extend(["--case", case_name])
    started = time.time()
    completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, check=False)
    if args.case and baseline_report is not None and report_path.exists():
        partial_report = load_json(report_path)
        merged_report = merge_case_reports(baseline_report, partial_report)
        report_path.write_text(json.dumps(merged_report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report_path.exists():
        result = collect_suite(
            suite,
            output_dir,
            recursive_target_scan=False,
            max_report_age_seconds=args.max_report_age_seconds,
            require_opensearch_target=(
                suite.needs_opensearch
                or (suite.accepts_optional_opensearch and bool(args.opensearch_url))
            ),
        )
    else:
        result = summarize_suite(suite, load_json(ROOT / suite.fixture), None)
        result["fixture_path"] = str(ROOT / suite.fixture)
        result["report_path"] = str(report_path)
        result["report_source"] = "missing"
        result["rerun"] = suite_rerun_commands(suite, output_dir, result.get("case_gaps", {}))
        result["note"] = "live runner did not produce the expected report"
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


def suite_run_command(
    suite: Suite,
    output_dir: Path,
    args: argparse.Namespace,
    report_path: Path,
) -> list[str]:
    if suite.runner_kind == "security-harness":
        command = [
            str(ROOT / suite.runner),
            "--steelsearch-url",
            args.steelsearch_url.rstrip("/"),
            "--fixture",
            str(ROOT / suite.fixture),
            suite.output_arg,
            str(report_path),
            "--report-dir",
            str(output_dir),
        ]
        if (suite.needs_opensearch or suite.accepts_optional_opensearch) and args.opensearch_url:
            command.extend(["--opensearch-url", args.opensearch_url.rstrip("/")])
        return command

    if suite.runner_kind == "multi-node":
        node_a_url = args.node_a_url or args.steelsearch_url
        node_b_url = args.node_b_url or ""
        command = [
            sys.executable,
            str(ROOT / suite.runner),
            "--node-a-url",
            node_a_url.rstrip("/"),
            "--fixture",
            str(ROOT / suite.fixture),
            suite.output_arg,
            str(report_path),
            "--timeout",
            str(args.timeout),
        ]
        if node_b_url:
            command.extend(["--node-b-url", node_b_url.rstrip("/")])
        if (suite.needs_opensearch or suite.accepts_optional_opensearch) and args.opensearch_url:
            command.extend(["--opensearch-url", args.opensearch_url.rstrip("/")])
        return command

    command = [
        sys.executable,
        str(ROOT / suite.runner),
        "--steelsearch-url",
        args.steelsearch_url.rstrip("/"),
    ]
    if suite.needs_opensearch or (suite.accepts_optional_opensearch and args.opensearch_url):
        command.extend(["--opensearch-url", args.opensearch_url.rstrip("/")])
    command.extend(
        [
            "--fixture",
            str(ROOT / suite.fixture),
            suite.output_arg,
            str(report_path),
            "--timeout",
            str(args.timeout),
        ]
    )
    return command


def suite_supports_case_filter(suite: Suite) -> bool:
    return suite.runner_kind not in {"security-harness", "multi-node"}


def collect_suite(
    suite: Suite,
    output_dir: Path,
    note: str | None = None,
    recursive_target_scan: bool = True,
    max_report_age_seconds: float | None = None,
    require_opensearch_target: bool | None = None,
    report_index: dict[str, list[Path]] | None = None,
) -> dict[str, Any]:
    fixture_path = ROOT / suite.fixture
    fixture = load_json(fixture_path)
    fixture_case_names = {
        str(case.get("name"))
        for case in fixture.get("cases") or []
        if isinstance(case, dict) and case.get("name")
    }
    expected_case_names = set(suite.default_cases) if suite.default_cases else fixture_case_names
    report_path, source, report, unusable_path = load_best_report(
        report_names_for_suite(suite),
        fixture_path,
        output_dir,
        recursive_target_scan,
        require_opensearch_target=suite.needs_opensearch
        if require_opensearch_target is None
        else require_opensearch_target,
        max_report_age_seconds=max_report_age_seconds,
        expected_case_names=expected_case_names,
        report_index=report_index,
    )
    result = summarize_suite(suite, fixture, report)
    result["fixture_path"] = str(fixture_path)
    result["report_path"] = str(report_path) if report_path is not None else str(output_dir / suite.report)
    result["report_source"] = source if report is not None else "missing"
    result["rerun"] = suite_rerun_commands(suite, output_dir, result.get("case_gaps", {}))
    if report is None and unusable_path is not None:
        result["note"] = f"ignored existing report because every recorded target request failed before receiving an HTTP status: {unusable_path}"
    if report is None and max_report_age_seconds is not None and unusable_path is None:
        result["note"] = f"no suite report satisfied max_report_age_seconds={max_report_age_seconds:g}"
    if note:
        result["note"] = note
    return result


def report_names_for_suite(suite: Suite) -> tuple[str, ...]:
    names = [suite.report]
    names.extend(suite.report_aliases)
    if (
        suite.runner == "tools/search_compat.py"
        and suite.report != "search-compat-report.json"
        and not suite.allow_partial_report
    ):
        names.append("search-compat-report.json")
    return tuple(names)


def build_target_report_index(suites: Sequence[Suite]) -> dict[str, list[Path]]:
    report_names = {
        report_name
        for suite in suites
        for report_name in report_names_for_suite(suite)
    }
    index = {report_name: [] for report_name in report_names}
    target_root = ROOT / "target"
    if not target_root.exists():
        return index
    for path in target_root.rglob("*.json"):
        if path.name in index and path.is_file():
            index[path.name].append(path)
    return index


def load_best_report(
    report_name: str | Sequence[str],
    fixture_path: Path,
    output_dir: Path,
    recursive_target_scan: bool,
    exclude_paths: set[Path] | None = None,
    require_opensearch_target: bool = False,
    max_report_age_seconds: float | None = None,
    expected_case_names: set[str] | None = None,
    report_index: dict[str, list[Path]] | None = None,
) -> tuple[Path | None, str | None, dict[str, Any] | None, Path | None]:
    report_names = (report_name,) if isinstance(report_name, str) else tuple(report_name)
    candidates: list[tuple[Path, str]] = []
    for candidate_report_name in report_names:
        output_report = output_dir / candidate_report_name
        if output_report.exists():
            candidates.append((output_report, "output-dir"))
        target_report = ROOT / "target" / candidate_report_name
        if target_report.exists():
            candidates.append((target_report, "target"))
        if recursive_target_scan:
            if report_index is not None:
                candidates.extend(
                    (path, "target-recursive")
                    for path in report_index.get(candidate_report_name, [])
                )
            else:
                candidates.extend(
                    (path, "target-recursive")
                    for path in (ROOT / "target").glob(f"**/{candidate_report_name}")
                    if path.is_file()
                )
    if not candidates:
        return None, None, None, None

    seen: set[Path] = set()
    unique_candidates = []
    for path, source in candidates:
        resolved = path.resolve()
        if exclude_paths and resolved in exclude_paths:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        unique_candidates.append((path, source))

    fixture = load_json(fixture_path)
    unusable_path = None
    usable_candidates: list[tuple[tuple[int, int, int, int, int, float], Path, str, dict[str, Any]]] = []
    newest_stale_path = None
    newest_stale_mtime = 0.0
    now = time.time()
    for path, source in unique_candidates:
        mtime = path.stat().st_mtime
        if max_report_age_seconds is not None and now - mtime > max_report_age_seconds:
            if mtime > newest_stale_mtime:
                newest_stale_path = path
                newest_stale_mtime = mtime
            continue
        report = load_json(path)
        if report_fixture_mismatch(report, fixture_path):
            continue
        if require_opensearch_target and "opensearch" not in (report.get("targets") or {}):
            continue
        if report_has_no_reachable_targets(report):
            unusable_path = path
            continue
        usable_candidates.append((report_quality_key(report, fixture, path, expected_case_names), path, source, report))
    if usable_candidates:
        _, path, source, report = max(usable_candidates, key=lambda item: item[0])
        merged_report = merge_missing_case_reports_from_candidates(
            report,
            usable_candidates,
            expected_case_names=expected_case_names,
        )
        if merged_report != report:
            return path, f"{source}+merged", merged_report, unusable_path
        return path, source, report, unusable_path
    if newest_stale_path is not None and unusable_path is None:
        return newest_stale_path, None, None, None
    return unusable_path, None, None, unusable_path


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def report_quality_key(
    report: dict[str, Any],
    fixture: dict[str, Any],
    path: Path,
    expected_case_names: set[str] | None = None,
) -> tuple[int, int, int, int, int, float]:
    fixture_names = {
        case.get("name")
        for case in fixture.get("cases") or []
        if isinstance(case, dict) and case.get("name")
    }
    if expected_case_names:
        fixture_names &= expected_case_names
    report_cases = [
        case
        for case in report.get("cases") or []
        if isinstance(case, dict) and case.get("name")
    ]
    report_names = {case.get("name") for case in report_cases}
    covered = len(fixture_names & report_names)
    missing = len(fixture_names - report_names)
    extra = len(report_names - fixture_names)
    failed = sum(1 for case in report_cases if case.get("status") == "failed")
    skipped = sum(1 for case in report_cases if case.get("status") == "skipped")
    return (covered, -failed, -missing, -extra, -skipped, path.stat().st_mtime)


def merge_case_reports(base: dict[str, Any], partial: dict[str, Any]) -> dict[str, Any]:
    merged = json.loads(json.dumps(base))
    for field in ("name", "fixture", "targets"):
        if field in partial:
            merged[field] = partial[field]

    cases_by_name = {
        case.get("name"): case
        for case in merged.get("cases", [])
        if isinstance(case, dict) and case.get("name")
    }
    for case in partial.get("cases", []):
        if isinstance(case, dict) and case.get("name"):
            cases_by_name[case["name"]] = case
    merged["cases"] = list(cases_by_name.values())
    merged["summary"] = recompute_case_summary(merged["cases"], merged.get("summary") or {})
    return merged


def merge_missing_case_reports_from_candidates(
    base: dict[str, Any],
    candidates: Sequence[tuple[tuple[int, int, int, int, int, float], Path, str, dict[str, Any]]],
    expected_case_names: set[str] | None = None,
) -> dict[str, Any]:
    merged = json.loads(json.dumps(base))
    cases_by_name = {
        case.get("name"): case
        for case in merged.get("cases", [])
        if isinstance(case, dict) and case.get("name")
    }
    for _quality, _path, _source, report in sorted(candidates, key=lambda item: item[0], reverse=True):
        for case in report.get("cases", []):
            if not isinstance(case, dict) or not case.get("name"):
                continue
            if expected_case_names and case["name"] not in expected_case_names:
                continue
            existing = cases_by_name.get(case["name"])
            if existing is None or case_merge_rank(case) > case_merge_rank(existing):
                cases_by_name[case["name"]] = case
    merged["cases"] = list(cases_by_name.values())
    merged["summary"] = recompute_case_summary(merged["cases"], merged.get("summary") or {})
    return merged


def case_status_rank(case: dict[str, Any]) -> int:
    return {
        "failed": 0,
        "skipped": 1,
        "passed": 2,
    }.get(str(case.get("status") or ""), -1)


def case_merge_rank(case: dict[str, Any]) -> tuple[int, int]:
    return (
        case_status_rank(case),
        1 if case_has_opensearch_evidence(case, False) else 0,
    )


def recompute_case_summary(cases: list[dict[str, Any]], original: dict[str, Any]) -> dict[str, Any]:
    summary = dict(original)
    passed = sum(1 for case in cases if case.get("status") == "passed")
    failed = sum(1 for case in cases if case.get("status") == "failed")
    skipped = sum(1 for case in cases if case.get("status") == "skipped")
    summary.update({"passed": passed, "failed": failed, "skipped": skipped})

    if any("area" in case for case in cases):
        by_area: dict[str, dict[str, int]] = {}
        for case in cases:
            area = str(case.get("area") or "unknown")
            area_summary = by_area.setdefault(area, {"passed": 0, "failed": 0, "skipped": 0})
            status = case.get("status")
            if status in area_summary:
                area_summary[status] += 1
        summary["by_area"] = by_area
    return summary


def report_fixture_mismatch(report: dict[str, Any], expected_fixture: Path) -> bool:
    fixture = report.get("fixture")
    if not isinstance(fixture, str) or not fixture:
        return False
    return Path(fixture).resolve() != expected_fixture.resolve()


def report_has_no_reachable_targets(report: dict[str, Any]) -> bool:
    cases = report.get("cases")
    if not isinstance(cases, list) or not cases:
        return False
    target_pairs = []
    for case in cases:
        if not isinstance(case, dict):
            continue
        steelsearch = case.get("steelsearch")
        opensearch = case.get("opensearch")
        if isinstance(steelsearch, dict) and isinstance(opensearch, dict):
            target_pairs.append((steelsearch, opensearch))
            continue
        targets = case.get("targets")
        if isinstance(targets, dict):
            steelsearch = targets.get("steelsearch")
            opensearch = targets.get("opensearch")
            if isinstance(steelsearch, dict) and isinstance(opensearch, dict):
                target_pairs.append((steelsearch, opensearch))
    if not target_pairs:
        return False
    return all(unreachable_response(left) and unreachable_response(right) for left, right in target_pairs)


def unreachable_response(response: dict[str, Any]) -> bool:
    status = response.get("status")
    result = response.get("result")
    if isinstance(result, dict):
        status = result.get("status", status)
    raw_response = response.get("raw_response")
    if isinstance(raw_response, dict):
        status = raw_response.get("status", status)
    return status in (None, 0)


def suite_rerun_commands(suite: Suite, output_dir: Path, case_gaps: dict[str, Any] | None = None) -> dict[str, str]:
    target_cases = list((case_gaps or {}).get("missing") or []) or list(suite.default_cases)
    unified = [sys.executable, "tools/run-unified-opensearch-e2e.py", "--run", "--suite", suite.name, "--output-dir", str(output_dir)]
    if suite.runner_kind == "multi-node":
        unified.extend(["--node-a-url", "${STEELSEARCH_NODE_A_URL}", "--node-b-url", "${STEELSEARCH_NODE_B_URL}"])
    else:
        unified.extend(["--steelsearch-url", "${STEELSEARCH_URL}"])
    if suite.needs_opensearch or suite.accepts_optional_opensearch:
        unified.extend(["--opensearch-url", "${OPENSEARCH_URL}"])
    if suite_supports_case_filter(suite):
        for case_name in target_cases:
            unified.extend(["--case", case_name])

    direct: list[str] = []
    if suite.runner is not None and suite.runner_kind == "multi-node":
        direct = [
            sys.executable,
            suite.runner,
            "--node-a-url",
            "${STEELSEARCH_NODE_A_URL}",
            "--node-b-url",
            "${STEELSEARCH_NODE_B_URL}",
            "--fixture",
            suite.fixture,
            suite.output_arg,
            str(output_dir / suite.report),
        ]
        if suite.needs_opensearch or suite.accepts_optional_opensearch:
            direct.extend(["--opensearch-url", "${OPENSEARCH_URL}"])
    elif suite.runner is not None and suite.runner_kind == "security-harness":
        direct = [
            suite.runner,
            "--steelsearch-url",
            "${STEELSEARCH_URL}",
            "--fixture",
            suite.fixture,
            suite.output_arg,
            str(output_dir / suite.report),
            "--report-dir",
            str(output_dir),
        ]
        if suite.needs_opensearch or suite.accepts_optional_opensearch:
            direct.extend(["--opensearch-url", "${OPENSEARCH_URL}"])
    elif suite.runner is not None:
        direct = [
            sys.executable,
            suite.runner,
            "--steelsearch-url",
            "${STEELSEARCH_URL}",
        ]
        if suite.needs_opensearch:
            direct.extend(["--opensearch-url", "${OPENSEARCH_URL}"])
        direct.extend(
            [
                "--fixture",
                suite.fixture,
                suite.output_arg,
                str(output_dir / suite.report),
            ]
        )
        for case_name in target_cases:
            direct.extend(["--case", case_name])
    return {
        "unified_command": shell_join_with_env(unified),
        "direct_command": shell_join_with_env(direct) if direct else "",
    }


def shell_join_with_env(command: list[str]) -> str:
    return " ".join(
        token
        if token in {
            "${STEELSEARCH_URL}",
            "${OPENSEARCH_URL}",
            "${STEELSEARCH_NODE_A_URL}",
            "${STEELSEARCH_NODE_B_URL}",
        }
        else shlex.quote(token)
        for token in command
    )


def summarize_suite(suite: Suite, fixture: dict[str, Any], report: dict[str, Any] | None) -> dict[str, Any]:
    fixture_cases = list(fixture.get("cases") or [])
    aggregate_case = fixture.get("aggregate_case")
    if isinstance(aggregate_case, dict) and aggregate_case.get("name"):
        fixture_cases.append(aggregate_case)
    if suite.default_cases:
        default_case_names = set(suite.default_cases)
        fixture_cases = [
            case
            for case in fixture_cases
            if isinstance(case, dict) and case.get("name") in default_case_names
        ]
    report_cases = (report.get("cases") or []) if report is not None else []
    if suite.allow_partial_report and report_cases:
        report_names = {
            case.get("name")
            for case in report_cases
            if isinstance(case, dict) and case.get("name")
        }
        fixture_cases = [
            case
            for case in fixture_cases
            if isinstance(case, dict) and case.get("name") in report_names
        ]
    base = {
        "name": suite.name,
        "area": suite.area,
        "parity_section": suite.parity_section,
        "required": suite.required,
        "allow_partial_report": suite.allow_partial_report,
        "fixture_case_count": len(fixture_cases),
    }
    if report is None:
        return {
            **base,
            "status": "missing" if suite.required else "blocked",
            "summary": {"passed": 0, "failed": 0, "skipped": 0},
            "has_opensearch_target": False,
            "classification": empty_classification(),
            "classification_cases": empty_classification_cases(),
            "case_gaps": empty_case_gaps(),
            "passed_cases": [],
            "by_area": {},
        }
    reported_summary = report.get("summary") or {}
    has_opensearch = "opensearch" in (report.get("targets") or {})
    fixture_names = {
        case.get("name")
        for case in fixture_cases
        if isinstance(case, dict) and case.get("name")
    }
    report_cases_for_summary = [
        case
        for case in report_cases
        if not fixture_names
        or (isinstance(case, dict) and case.get("name") in fixture_names)
    ]
    has_extra_report_cases = len(report_cases_for_summary) != len(report_cases)
    summary = recompute_case_summary(report_cases_for_summary, reported_summary)
    summary_drift = {} if has_extra_report_cases else case_summary_drift(reported_summary, summary)
    failed = int(summary.get("failed") or 0)
    skipped = int(summary.get("skipped") or 0)
    classification_cases = classify_case_names(fixture_cases, report_cases, has_opensearch)
    classification = {key: len(value) for key, value in classification_cases.items()}
    case_gaps = collect_case_gaps(fixture_cases, report_cases)
    missing = int(classification.get("missing") or 0)
    classified_failed = int(classification.get("failed") or 0)
    status = "ok" if failed == 0 and classified_failed == 0 and missing == 0 else "failed"
    if skipped and failed == 0 and classified_failed == 0:
        status = "ok"
    if missing and failed == 0 and classified_failed == 0:
        status = "missing"
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
        "classification_cases": classification_cases,
        "case_gaps": case_gaps,
        "passed_cases": collect_passed_cases(fixture_cases, report_cases),
        "summary_drift": summary_drift,
        "by_area": summary.get("by_area") or {},
    }


def case_summary_drift(reported: dict[str, Any], recomputed: dict[str, Any]) -> dict[str, dict[str, int]]:
    drift: dict[str, dict[str, int]] = {}
    for key in ("passed", "failed", "skipped"):
        reported_value = int(reported.get(key) or 0)
        recomputed_value = int(recomputed.get(key) or 0)
        if reported_value != recomputed_value:
            drift[key] = {
                "reported": reported_value,
                "recomputed": recomputed_value,
            }
    return drift


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


def empty_classification_cases() -> dict[str, list[str]]:
    return {key: [] for key in empty_classification()}


def empty_case_gaps() -> dict[str, list[str]]:
    return {
        "missing": [],
        "extra": [],
        "failed": [],
        "skipped": [],
        "fail_closed": [],
    }


def classify_cases(fixture_cases: list[dict[str, Any]], report_cases: list[dict[str, Any]], has_opensearch: bool) -> dict[str, int]:
    return {key: len(value) for key, value in classify_case_names(fixture_cases, report_cases, has_opensearch).items()}


def classify_case_names(
    fixture_cases: list[dict[str, Any]],
    report_cases: list[dict[str, Any]],
    has_opensearch: bool,
) -> dict[str, list[str]]:
    cases = empty_classification_cases()
    fixture_by_name = {case.get("name"): case for case in fixture_cases}
    report_by_name = {case.get("name"): case for case in report_cases}
    for name, fixture_case in fixture_by_name.items():
        case_name = str(name)
        report_case = report_by_name.get(name)
        if report_case is None:
            cases["missing"].append(case_name)
            continue
        status = report_case.get("status")
        if status == "failed":
            cases["failed"].append(case_name)
            continue
        if status == "skipped":
            cases["known_gap_or_skipped"].append(case_name)
            continue
        if status != "passed":
            cases["failed"].append(case_name)
            continue
        if fixture_case.get("comparison") == "steelsearch_only":
            expected_status = fixture_case.get("expected_steelsearch_status")
            if isinstance(expected_status, int) and expected_status >= 400:
                cases["steelsearch_fail_closed"].append(case_name)
            else:
                cases["steelsearch_only"].append(case_name)
            continue
        if not case_has_opensearch_evidence(report_case, has_opensearch):
            cases["steelsearch_only"].append(case_name)
        elif fixture_case.get("strict_source_parity_required") is True:
            cases["strict_equal"].append(case_name)
        elif fixture_case.get("expect_hits") is not None or fixture_case.get("expected_steelsearch_status") is not None:
            cases["semantic_equal"].append(case_name)
        else:
            cases["canonical_equal"].append(case_name)
    return {key: sorted(value) for key, value in cases.items()}


def case_has_opensearch_evidence(report_case: dict[str, Any], suite_has_opensearch: bool) -> bool:
    if report_case.get("mode") == "steelsearch-only" or "opensearch_unmatched" in report_case:
        return False
    targets = report_case.get("targets")
    if isinstance(targets, dict):
        return isinstance(targets.get("opensearch"), dict)
    if isinstance(report_case.get("opensearch"), dict):
        return True
    return suite_has_opensearch


def collect_case_gaps(fixture_cases: list[dict[str, Any]], report_cases: list[dict[str, Any]]) -> dict[str, list[str]]:
    fixture_names = {str(case.get("name")) for case in fixture_cases if case.get("name")}
    report_by_name = {
        str(case.get("name")): case
        for case in report_cases
        if isinstance(case, dict) and case.get("name")
    }
    missing = sorted(fixture_names - set(report_by_name))
    extra = sorted(set(report_by_name) - fixture_names)
    failed = sorted(
        name
        for name, case in report_by_name.items()
        if name in fixture_names
        and case.get("status") not in {"passed", "skipped"}
    )
    skipped = sorted(
        name
        for name, case in report_by_name.items()
        if name in fixture_names and case.get("status") == "skipped"
    )
    fail_closed = sorted(
        str(case.get("name"))
        for case in fixture_cases
        if case.get("name")
        and case.get("comparison") == "steelsearch_only"
        and isinstance(case.get("expected_steelsearch_status"), int)
        and int(case.get("expected_steelsearch_status")) >= 400
        and (report_by_name.get(str(case.get("name"))) or {}).get("status") == "passed"
    )
    return {
        "missing": missing,
        "extra": extra,
        "failed": failed,
        "skipped": skipped,
        "fail_closed": fail_closed,
    }


def collect_passed_cases(fixture_cases: list[dict[str, Any]], report_cases: list[dict[str, Any]]) -> list[str]:
    fixture_names = {str(case.get("name")) for case in fixture_cases if case.get("name")}
    passed = [
        str(case.get("name"))
        for case in report_cases
        if isinstance(case, dict)
        and case.get("name") in fixture_names
        and case.get("status") == "passed"
    ]
    return sorted(passed)


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
    gap_resolution = resolve_cross_suite_skips(suite_results)
    effective_totals = dict(totals)
    effective_totals["known_gap_or_skipped"] = max(
        0,
        effective_totals["known_gap_or_skipped"] - gap_resolution["skipped"]["resolved_by_other_suite_count"],
    )
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
            "effective_case_classification": effective_totals,
            "case_gap_resolution": gap_resolution,
        },
        "suite_results": suite_results,
    }


def resolve_cross_suite_skips(suite_results: list[dict[str, Any]]) -> dict[str, Any]:
    passed_by_case: dict[str, list[str]] = {}
    for suite in suite_results:
        if not suite.get("required"):
            continue
        if suite.get("status") != "ok":
            continue
        for case_name in suite.get("passed_cases") or []:
            passed_by_case.setdefault(str(case_name), []).append(str(suite["name"]))

    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    total_skipped = 0
    for suite in suite_results:
        if not suite.get("required"):
            continue
        skipped_cases = (suite.get("case_gaps") or {}).get("skipped") or []
        for case_name in skipped_cases:
            total_skipped += 1
            covering_suites = [
                candidate
                for candidate in passed_by_case.get(str(case_name), [])
                if candidate != suite.get("name")
            ]
            entry = {
                "case": str(case_name),
                "suite": str(suite.get("name")),
            }
            if covering_suites:
                resolved.append({**entry, "covered_by": covering_suites})
            else:
                unresolved.append(entry)
    return {
        "skipped": {
            "total_count": total_skipped,
            "resolved_by_other_suite_count": len(resolved),
            "unresolved_count": len(unresolved),
            "resolved": resolved,
            "unresolved": unresolved,
        }
    }


def section_summary(section_name: str, suite_results: list[dict[str, Any]]) -> dict[str, Any]:
    suites = [suite for suite in suite_results if suite["parity_section"] == section_name]
    required = [suite for suite in suites if suite["required"]]
    missing = [
        suite
        for suite in required
        if suite["report_source"] == "missing" or suite["classification"].get("missing", 0)
    ]
    failed = [
        suite
        for suite in required
        if suite["summary"]["failed"] or suite["status"] in {"blocked", "failed"}
    ]
    status = "ok"
    if failed:
        status = "blocked"
    elif missing:
        status = "missing"
    return {
        "required_suites": [suite["name"] for suite in required],
        "report_paths": [suite["report_path"] for suite in required],
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
    gap_suites = [
        suite
        for suite in report["suite_results"]
        if any(suite.get("case_gaps", {}).values())
    ]
    if gap_suites:
        lines.extend(["", "## Case Gaps", ""])
        for suite in gap_suites:
            gaps = suite.get("case_gaps", {})
            lines.append(f"### {suite['name']}")
            rerun = suite.get("rerun") or {}
            if rerun.get("unified_command"):
                lines.extend(["", "Unified rerun:", "", "```bash", rerun["unified_command"], "```", ""])
            if rerun.get("direct_command"):
                lines.extend(["Direct runner:", "", "```bash", rerun["direct_command"], "```", ""])
            for key in ("missing", "failed", "skipped", "extra"):
                values = gaps.get(key) or []
                if not values:
                    continue
                lines.append(f"- {key}: {len(values)}")
                lines.extend(f"  - `{value}`" for value in values)
            lines.append("")
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
