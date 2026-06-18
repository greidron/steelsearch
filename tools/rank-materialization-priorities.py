#!/usr/bin/env python3
"""Rank operation-level materialization fallback priorities from load reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


COUNTERS = (
    "compatibility_materialized_response_fetches",
    "materialized_response_fetches",
)

OPERATION_FAMILIES = {
    "fallback_query_string": "query_string/simple_query_string compatibility materialization",
    "lexical": "lexical query materialization",
    "ranking": "ranking query materialization",
    "facet": "aggregation materialization",
    "sort_filter": "sort/filter materialization",
    "nested": "nested query materialization",
    "vector": "vector query materialization",
    "hybrid": "hybrid vector query materialization",
    "write": "write-path resource baseline",
    "refresh": "refresh-path resource baseline",
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="load-baseline or search-benchmark-matrix JSON report")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--min-compat-delta", type=int, default=1)
    parser.add_argument("--allow-empty", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = json.loads(args.report.read_text(encoding="utf-8"))
    report = build_priority_report(payload, args.min_compat_delta, allow_empty=args.allow_empty)
    text = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report["summary"]["passed"] else 1


def build_priority_report(
    payload: dict[str, Any],
    min_compat_delta: int = 1,
    *,
    allow_empty: bool = False,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for scenario, operations in iter_operation_payloads(payload):
        for operation, op_payload in operations.items():
            success_count = numeric(op_payload.get("success_count"))
            if success_count <= 0:
                continue
            resource_usage = op_payload.get("resource_usage")
            if not isinstance(resource_usage, dict):
                continue
            counter_payloads = {
                counter: counter_summary(resource_usage, counter, success_count)
                for counter in COUNTERS
            }
            compat_delta = counter_payloads["compatibility_materialized_response_fetches"]["delta"]
            if compat_delta < min_compat_delta:
                continue
            rows.append(
                {
                    "scenario": scenario,
                    "operation": operation,
                    "family": OPERATION_FAMILIES.get(operation, f"{operation} materialization"),
                    "success_count": success_count,
                    "counters": counter_payloads,
                    "priority_score": priority_score(counter_payloads),
                }
            )
    rows.sort(
        key=lambda row: (
            row["counters"]["compatibility_materialized_response_fetches"]["per_success"],
            row["counters"]["compatibility_materialized_response_fetches"]["delta"],
            row["counters"]["materialized_response_fetches"]["per_success"],
        ),
        reverse=True,
    )
    for rank, row in enumerate(rows, start=1):
        row["rank"] = rank
    return {
        "summary": {
            "passed": len(rows) > 0 or allow_empty,
            "allow_empty": allow_empty,
            "ranked_operation_count": len(rows),
            "min_compat_delta": min_compat_delta,
            "top_family": rows[0]["family"] if rows else None,
            "top_operation": rows[0]["operation"] if rows else None,
        },
        "priorities": rows,
    }


def iter_operation_payloads(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    scenarios = payload.get("scenarios")
    if isinstance(scenarios, dict):
        return [
            (scenario, scenario_payload.get("operations", {}))
            for scenario, scenario_payload in scenarios.items()
            if isinstance(scenario_payload, dict) and isinstance(scenario_payload.get("operations"), dict)
        ]
    operations = payload.get("operations")
    if isinstance(operations, dict):
        base_url = payload.get("config", {}).get("base_url", "load-baseline")
        return [(str(base_url), operations)]
    return []


def counter_summary(resource_usage: dict[str, Any], counter: str, success_count: float) -> dict[str, Any]:
    delta = numeric((resource_usage.get(counter) or {}).get("delta"))
    return {
        "delta": delta,
        "per_success": delta / success_count if success_count > 0 else 0.0,
    }


def priority_score(counters: dict[str, dict[str, float]]) -> float:
    return (
        counters["compatibility_materialized_response_fetches"]["per_success"] * 1000.0
        + counters["materialized_response_fetches"]["per_success"]
    )


def numeric(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Materialization Priority Report",
        "",
        "| Rank | Scenario | Operation | Family | Compatibility delta/op | Materialized delta/op |",
        "|---:|---|---|---|---:|---:|",
    ]
    for row in report["priorities"]:
        compat = row["counters"]["compatibility_materialized_response_fetches"]
        materialized = row["counters"]["materialized_response_fetches"]
        lines.append(
            "| {rank} | `{scenario}` | `{operation}` | {family} | {compat:.2f} | {materialized:.2f} |".format(
                rank=row["rank"],
                scenario=row["scenario"],
                operation=row["operation"],
                family=row["family"],
                compat=compat["per_success"],
                materialized=materialized["per_success"],
            )
        )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    sys.exit(main())
