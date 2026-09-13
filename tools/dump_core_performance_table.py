#!/usr/bin/env python3
"""Render the latest verified repeated core benchmark as a one-direction status table."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from core_performance_budget import METRICS
from release_notes import OPERATIONS, TOPOLOGIES


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESULTS_ROOT = ROOT / "target/core-replacement-c06"
DEFAULT_OUTPUT = ROOT / "docs/rust-port/current-core-performance-status.md"


def load(path: Path) -> dict:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected an object")
    return value


def completed_result(path: Path) -> bool:
    try:
        result = load(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return False
    return (
        result.get("execution_inputs_verified") is True
        and isinstance(result.get("checks"), list)
        and len(result["checks"]) == 2
        and "error" not in result
    )


def latest_result(root: Path) -> Path:
    candidates = [path for path in root.glob("*/result.json") if completed_result(path)]
    if not candidates:
        raise ValueError(f"no completed, execution-verified result under {root}")
    return max(candidates, key=lambda path: path.stat().st_mtime)


def relative_ratio(direction: str, baseline: str, candidate: str) -> Decimal:
    before = Decimal(baseline)
    after = Decimal(candidate)
    if direction == "higher":
        return after / before
    if direction == "lower":
        return before / after
    raise ValueError(f"unknown metric direction: {direction}")


def range_label(values: list[Decimal]) -> str:
    ordered = sorted(values)
    low, high = (value.quantize(Decimal("0.001")) for value in (ordered[0], ordered[-1]))
    return f"{low}x" if low == high else f"{low}-{high}x"


def minimum_label(values: list[Decimal]) -> str:
    return f"{min(values).quantize(Decimal('0.001'))}x"


def metric_indexes(result: dict) -> dict[str, dict[str, list[Decimal]]]:
    values = {metric: {"v060": [], "opensearch": []} for metric in METRICS}
    for check in result["checks"]:
        published = check.get("published")
        if not isinstance(published, dict):
            raise ValueError("result check has no published v0.6.0 comparison")
        rows = published.get("metrics")
        reference = published.get("opensearch_metrics")
        if not isinstance(rows, list) or not isinstance(reference, dict):
            raise ValueError("result check has incomplete metric evidence")
        by_name = {row.get("metric"): row for row in rows if isinstance(row, dict)}
        if set(by_name) != set(METRICS):
            raise ValueError("result check does not contain all 44 core metrics")
        for metric, direction in METRICS.items():
            row = by_name[metric]
            candidate = row.get("candidate")
            baseline = row.get("baseline")
            opensearch = reference.get(metric)
            if not all(isinstance(value, str) for value in (candidate, baseline, opensearch)):
                raise ValueError(f"{metric}: incomplete numeric evidence")
            values[metric]["v060"].append(relative_ratio(direction, baseline, candidate))
            values[metric]["opensearch"].append(relative_ratio(direction, opensearch, candidate))
    return values


def render(result_path: Path, result: dict) -> str:
    values = metric_indexes(result)
    plan = load(result_path.parent / "plan.json")
    candidate = plan["binaries"]["candidate"]["sha256"]
    created = datetime.fromtimestamp(plan["created_at_epoch"], timezone.utc).isoformat()
    failed = sum(min(scores["v060"]) < Decimal("0.95") for scores in values.values())
    rows = [
        "# Current Core Performance Status",
        "",
        "This file is generated from the latest completed, execution-verified repeated non-plugin benchmark.",
        "",
        "- Ratio `1.000x` means equal performance. Higher is faster for every row.",
        "- Throughput ratio = candidate/reference. Latency ratio = reference/candidate.",
        "- Each cell is the two-run range; the lower endpoint is the conservative value.",
        "- `took` is excluded. This is not a release approval or implementation-acceptance record.",
        f"- Source: `{result_path.relative_to(ROOT)}`.",
        f"- Benchmark plan: {created}; candidate SHA-256: `{candidate}`.",
        f"- Fixed v0.6.0 gate: {failed}/44 measured values have a two-run lower ratio below 0.950x.",
        "",
        "## At A Glance",
        "",
        "Each value is the conservative lowest ratio. `1.000x` is equal; higher is faster.",
        "Scenario rows use the worst of mean, p95, and p99 across both repetitions.",
    ]
    for topology in TOPOLOGIES:
        topology_label = "Single Node" if topology == "single-node" else "3 Nodes"
        rows.extend([
            "",
            f"### {topology_label}",
            "",
            "| Scenario | vs v0.6.0 | vs OpenSearch |",
            "| --- | ---: | ---: |",
        ])
        throughput = values[f"{topology}/throughput"]
        rows.append(
            "| throughput | "
            f"{minimum_label(throughput['v060'])} | "
            f"{minimum_label(throughput['opensearch'])} |"
        )
        for operation in OPERATIONS:
            def scenario_minimum(reference):
                return minimum_label([
                    ratio
                    for percentile in ("mean", "p95", "p99")
                    for ratio in values[f"{topology}/{operation}/{percentile}"][reference]
                ])

            rows.append(
                f"| {operation} latency | {scenario_minimum('v060')} | "
                f"{scenario_minimum('opensearch')} |"
            )
    rows.extend([
        "",
        "<details>",
        "<summary>Detailed ranges: mean / p95 / p99</summary>",
        "",
        "## Detailed Measurements",
        "",
        "Rows are `mean / p95 / p99` performance ratios, all with the same higher-is-faster direction.",
        "",
        "| Topology | Scenario | v0.6.0 ratio (mean / p95 / p99) | OpenSearch ratio (mean / p95 / p99) |",
        "| --- | --- | ---: | ---: |",
    ])
    for topology in TOPOLOGIES:
        for operation in OPERATIONS:
            baseline = []
            opensearch = []
            for percentile in ("mean", "p95", "p99"):
                scores = values[f"{topology}/{operation}/{percentile}"]
                baseline.append(range_label(scores["v060"]))
                opensearch.append(range_label(scores["opensearch"]))
            rows.append(f"| {topology} | {operation} | {' / '.join(baseline)} | {' / '.join(opensearch)} |")
    rows.extend(["", "</details>"])
    return "\n".join(rows) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, help="explicit completed result.json")
    parser.add_argument("--results-root", type=Path, default=DEFAULT_RESULTS_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result_path = args.result.resolve() if args.result else latest_result(args.results_root.resolve())
    if not completed_result(result_path):
        parser.error(f"not a completed, execution-verified result: {result_path}")
    content = render(result_path, load(result_path))
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(output)
    print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
