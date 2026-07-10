#!/usr/bin/env python3
"""Validate the runtime peer backpressure evidence report."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_PROFILE = "mixed-java-rust-query-phase"
REQUIRED_READBACK_COUNT = 4


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    result = validate_report(payload)
    print(json.dumps({"report": str(args.report), **result}, indent=2, sort_keys=True))
    return 0 if result["status"] == "ok" else 1


def validate_report(payload: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
    profile = payload.get("profile") if isinstance(payload.get("profile"), dict) else {}
    results = payload.get("results") if isinstance(payload.get("results"), dict) else {}

    if summary.get("passed") is not True:
        errors.append("summary.passed is not true")
    if summary.get("profile") != REQUIRED_PROFILE:
        errors.append(f"summary.profile is not {REQUIRED_PROFILE}")
    if profile.get("name") != REQUIRED_PROFILE:
        errors.append(f"profile.name is not {REQUIRED_PROFILE}")
    required_readbacks = profile.get("required_readbacks")
    if not isinstance(required_readbacks, list) or len(required_readbacks) < REQUIRED_READBACK_COUNT:
        errors.append("profile.required_readbacks is incomplete")

    steelsearch = results.get("steelsearch") if isinstance(results.get("steelsearch"), dict) else {}
    opensearch = results.get("opensearch") if isinstance(results.get("opensearch"), dict) else {}
    if steelsearch.get("passed") is not True:
        errors.append("results.steelsearch.passed is not true")
    if opensearch.get("passed") is not True:
        errors.append("results.opensearch.passed is not true")
    if steelsearch.get("pool") != "remote_transport":
        errors.append("results.steelsearch.pool is not remote_transport")
    if opensearch.get("pool") != "search":
        errors.append("results.opensearch.pool is not search")

    steel_stats = steelsearch.get("node_stats") if isinstance(steelsearch.get("node_stats"), dict) else {}
    open_stats = opensearch.get("node_stats") if isinstance(opensearch.get("node_stats"), dict) else {}
    require_positive_counter(errors, steel_stats, "results.steelsearch.node_stats", "rejected")
    require_positive_counter(errors, steel_stats, "results.steelsearch.node_stats", "completed")
    require_positive_counter(errors, open_stats, "results.opensearch.node_stats", "rejected")
    require_positive_counter(errors, open_stats, "results.opensearch.node_stats", "completed")
    require_positive_counter(errors, steelsearch.get("active_row"), "results.steelsearch.active_row", "active")
    require_positive_counter(errors, steelsearch.get("rejected_row"), "results.steelsearch.rejected_row", "rejected")
    require_positive_counter(errors, steelsearch.get("completed_row"), "results.steelsearch.completed_row", "completed")
    require_opensearch_rejected_increase(errors, opensearch)
    require_positive_scalar(errors, opensearch, "results.opensearch", "http_429_count")
    require_http_429_sample(errors, opensearch)

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": summary.get("passed"),
            "profile": summary.get("profile"),
            "steelsearch_rejected": integer_value(steel_stats.get("rejected")),
            "steelsearch_completed": integer_value(steel_stats.get("completed")),
            "opensearch_rejected": integer_value(open_stats.get("rejected")),
            "opensearch_completed": integer_value(open_stats.get("completed")),
            "opensearch_http_429_count": integer_value(opensearch.get("http_429_count")),
        },
    }


def require_positive_counter(
    errors: list[str],
    stats: Any,
    path: str,
    field: str,
) -> None:
    if not isinstance(stats, dict):
        errors.append(f"{path}.{field} is missing or not an integer")
        return
    value = integer_value(stats.get(field))
    if value is None:
        errors.append(f"{path}.{field} is missing or not an integer")
    elif value < 1:
        errors.append(f"{path}.{field} is {value}, expected >= 1")


def require_positive_scalar(
    errors: list[str],
    payload: dict[str, Any],
    path: str,
    field: str,
) -> None:
    value = integer_value(payload.get(field))
    if value is None:
        errors.append(f"{path}.{field} is missing or not an integer")
    elif value < 1:
        errors.append(f"{path}.{field} is {value}, expected >= 1")


def require_opensearch_rejected_increase(errors: list[str], opensearch: dict[str, Any]) -> None:
    before = opensearch.get("before_row")
    after = opensearch.get("after_row")
    before_rejected = integer_value(before.get("rejected")) if isinstance(before, dict) else None
    after_rejected = integer_value(after.get("rejected")) if isinstance(after, dict) else None
    if before_rejected is None:
        errors.append("results.opensearch.before_row.rejected is missing or not an integer")
    if after_rejected is None:
        errors.append("results.opensearch.after_row.rejected is missing or not an integer")
    if before_rejected is not None and after_rejected is not None and after_rejected <= before_rejected:
        errors.append("results.opensearch rejected counter did not increase")


def require_http_429_sample(errors: list[str], opensearch: dict[str, Any]) -> None:
    samples = opensearch.get("error_samples")
    if not isinstance(samples, list) or not any(
        isinstance(sample, dict) and integer_value(sample.get("status")) == 429
        for sample in samples
    ):
        errors.append("results.opensearch 429 error sample is missing")


def integer_value(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


if __name__ == "__main__":
    sys.exit(main())
