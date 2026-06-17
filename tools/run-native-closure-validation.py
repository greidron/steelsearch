#!/usr/bin/env python3
"""Run native-closure validation batches and reject zero-test matches."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class ValidationTest:
    name: str
    group: str
    package: str = "os-engine-tantivy"
    target: tuple[str, ...] = ("--lib",)
    features: tuple[str, ...] = ()


COMPACT_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_bucket_sort_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_derivative_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_serial_diff_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "engine_collects_placeholder_for_malformed_plugin_bucket_count_request",
        "malformed-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_sort_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_bucket_count_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_derivative_surface",
        "date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_date_histogram_reduce_feeds_serial_diff_surface",
        "date-histogram-rebucketing-wrapper",
    ),
)

REBUCKETING_WIDE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_sort_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_bucket_count_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_derivative_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_auto_date_histogram_reduce_feeds_serial_diff_surface",
        "auto-date-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_sort_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_bucket_count_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_derivative_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_histogram_reduce_feeds_serial_diff_surface",
        "histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_sort_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_bucket_count_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_derivative_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
    ValidationTest(
        "search_size_zero_multi_index_plugin_variable_width_histogram_reduce_feeds_serial_diff_surface",
        "variable-width-histogram-rebucketing-wrapper",
    ),
)

VECTOR_KNN_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "engine_executes_knn_query_with_filter_and_vector_scores",
        "vector-knn-filter-score",
    ),
    ValidationTest(
        "engine_bounds_and_invalidates_knn_runtime_cache_entries",
        "vector-knn-cache",
    ),
    ValidationTest(
        "single_index_knn_uses_vector_native_page_and_aggregation_fetch",
        "single-index-vector-native-page-aggregation",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce",
        "multi-index-vector-native-page-aggregation",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_reduce_with_id_sort",
        "multi-index-vector-native-sort",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce_with_score_desc",
        "multi-index-vector-native-sort",
    ),
    ValidationTest(
        "multi_index_knn_uses_vector_native_page_and_aggregation_reduce_with_fast_field_sort",
        "multi-index-vector-native-sort",
    ),
)

STARTUP_PREFLIGHT_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "daemon_config_rejects_data_path_that_is_not_directory",
        "data-path-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_same_http_and_transport_socket",
        "bind-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_duplicate_development_node_ids",
        "identity-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_invalid_addresses",
        "config-parse-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_invalid_ports",
        "config-parse-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_non_cluster_manager_without_seed_hosts",
        "role-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_config_rejects_production_mode_without_required_gates",
        "production-gate-preflight",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_rejects_data_path_that_is_not_a_directory",
        "daemon-data-path-preflight",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "daemon_exits_when_http_port_is_occupied",
        "daemon-bind-preflight",
        package="os-node",
        target=("--test", "dev_cluster_daemons"),
        features=("standalone-runtime",),
    ),
)

RUNTIME_TASKS_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "tasks_live_route_supports_list_get_and_cancel_shapes",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--bin", "steelsearch"),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "tasks_cancel_route_supports_task_id_path_variant",
        "task-cancellation-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_QUEUE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "cluster_pending_tasks_route_surfaces_task_metadata_visibility",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
    ValidationTest(
        "cluster_health_tasks_and_cat_pending_tasks_share_runtime_queue_depth",
        "task-queue-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

RUNTIME_THROTTLE_BATCH: tuple[ValidationTest, ...] = (
    ValidationTest(
        "rethrottle_routes_support_task_id_path_variants",
        "task-throttle-runtime-state",
        package="os-node",
        target=("--lib",),
        features=("standalone-runtime",),
    ),
)

BATCHES: dict[str, tuple[ValidationTest, ...]] = {
    "compact": COMPACT_BATCH,
    "rebucketing-wide": REBUCKETING_WIDE_BATCH,
    "vector-knn": VECTOR_KNN_BATCH,
    "startup-preflight": STARTUP_PREFLIGHT_BATCH,
    "runtime-tasks": RUNTIME_TASKS_BATCH,
    "runtime-queue": RUNTIME_QUEUE_BATCH,
    "runtime-throttle": RUNTIME_THROTTLE_BATCH,
}

RUNNING_RE = re.compile(r"running (?P<count>\d+) tests?")
RESULT_RE = re.compile(
    r"test result: (?P<status>\w+)\. (?P<passed>\d+) passed; (?P<failed>\d+) failed;"
)


def parse_test_output(output: str) -> dict[str, Any]:
    running = 0
    passed = 0
    failed = 0
    status = "unknown"
    for line in output.splitlines():
        running_match = RUNNING_RE.search(line)
        if running_match:
            running = max(running, int(running_match.group("count")))
        result_match = RESULT_RE.search(line)
        if result_match:
            status = result_match.group("status")
            passed = int(result_match.group("passed"))
            failed = int(result_match.group("failed"))
    return {
        "running": running,
        "passed": passed,
        "failed": failed,
        "status": status,
    }


def run_test(test: ValidationTest) -> dict[str, Any]:
    command = [
        "cargo",
        "test",
        "-p",
        test.package,
    ]
    if test.features:
        command.extend(["--features", ",".join(test.features)])
    command.extend([
        *test.target,
        test.name,
    ])
    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    parsed = parse_test_output(completed.stdout)
    ok = completed.returncode == 0 and parsed["running"] > 0 and parsed["failed"] == 0
    return {
        "name": test.name,
        "group": test.group,
        "command": command,
        "returncode": completed.returncode,
        "ok": ok,
        **parsed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--batch",
        choices=tuple(BATCHES),
        default="compact",
        help="validation batch to run",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format",
    )
    args = parser.parse_args()

    tests = BATCHES[args.batch]
    results = [run_test(test) for test in tests]
    summary = {
        "batch": args.batch,
        "test_count": len(results),
        "passed_count": sum(1 for result in results if result["ok"]),
        "failed_count": sum(1 for result in results if not result["ok"]),
        "zero_test_count": sum(1 for result in results if result["running"] == 0),
    }
    report = {"summary": summary, "results": results}

    if args.format == "json":
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            "batch={batch} passed={passed_count}/{test_count} failed={failed_count} zero_tests={zero_test_count}".format(
                **summary
            )
        )
        for result in results:
            state = "ok" if result["ok"] else "failed"
            print(
                f"{state}\t{result['group']}\t{result['name']}\t"
                f"running={result['running']} passed={result['passed']} failed={result['failed']}"
            )

    return 0 if summary["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
