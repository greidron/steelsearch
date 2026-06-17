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

BATCHES: dict[str, tuple[ValidationTest, ...]] = {
    "compact": COMPACT_BATCH,
    "rebucketing-wide": REBUCKETING_WIDE_BATCH,
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
        "os-engine-tantivy",
        "--lib",
        test.name,
    ]
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
