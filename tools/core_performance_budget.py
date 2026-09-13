"""Numeric portion of the fixed-v0.6.0 budget; not an evidence acceptance gate."""

from decimal import Decimal
from math import isfinite

from release_notes import OPERATIONS, TOPOLOGIES, require


METRICS = {
    **{f"{topology}/throughput": "higher" for topology in TOPOLOGIES},
    **{
        f"{topology}/{operation}/{percentile}": "lower"
        for topology in TOPOLOGIES
        for operation in OPERATIONS
        for percentile in ("mean", "p95", "p99")
    },
}


def measurement(value, label: str) -> Decimal:
    require(type(value) in (int, float, Decimal), f"{label}: numeric measurement required")
    if isinstance(value, float):
        require(isfinite(value), f"{label}: finite measurement required")
    result = Decimal(str(value))
    require(result.is_finite() and result > 0, f"{label}: positive finite measurement required")
    return result


def compare_metrics(baseline: dict, candidate: dict) -> dict:
    """Compare all metrics without averaging away regressions or rounding limits.

    Callers must separately authenticate the baseline, validate raw counts and
    configurations, and prove that the complete prescribed suite was executed.
    """
    for name, values in (("baseline", baseline), ("candidate", candidate)):
        require(isinstance(values, dict) and set(values) == set(METRICS),
                f"{name}: exactly all 44 core metrics required")
    rows = []
    for key, direction in METRICS.items():
        before = measurement(baseline[key], f"baseline/{key}")
        after = measurement(candidate[key], f"candidate/{key}")
        if direction == "higher":
            limit = before * Decimal("0.95")
            passed = after >= limit
            regression = (before - after) / before * 100
        else:
            limit = before * Decimal("1.05")
            passed = after <= limit
            regression = (after - before) / before * 100
        rows.append({
            "metric": key,
            "direction": direction,
            "baseline": str(before),
            "candidate": str(after),
            "limit": str(limit),
            "regression_percent": str(regression),
            "within_budget": passed,
        })
    failures = [row["metric"] for row in rows if not row["within_budget"]]
    return {
        "scope": "numeric-only; baseline identity and full-run evidence not validated",
        "acceptance_established": False,
        "numeric_budget_passed": not failures,
        "failed_metrics": failures,
        "metrics": rows,
    }
