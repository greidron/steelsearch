#!/usr/bin/env python3
"""Report remaining non-native execution paths that are not format-only parity."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ENGINE_DOC = ROOT / "docs" / "rust-port" / "tantivy-native-gap-analysis.md"
PLAN_DOC = ROOT / "docs" / "rust-port" / "native-closure-execution-plan.md"
RUNTIME_DOC = ROOT / "docs" / "rust-port" / "node-runtime-gap-inventory.md"
SECURITY_DOC = ROOT / "docs" / "rust-port" / "production-security-baseline.md"
SHARD_PROBE = ROOT / "tools" / "probe_three_node_shard_movement.py"
ENGINE_SOURCE = ROOT / "crates" / "os-engine-tantivy" / "src" / "lib.rs"


@dataclass(frozen=True)
class Probe:
    name: str
    category: str
    path: Path
    patterns: tuple[str, ...]
    risk: str


PROBES: tuple[Probe, ...] = (
    Probe(
        name="source-backed query families",
        category="source-backed execution",
        path=ENGINE_DOC,
        patterns=(
            r"source-backed `nested`",
            r"source-backed `geo_distance`",
            r"source-backed `distance_feature`",
            r"source-backed `rank_feature`",
            r"source-backed `more_like_this`",
            r"source-backed `terms_set`",
            r"source-backed `query_string`",
            r"source-backed `simple_query_string`",
        ),
        risk="document/source evaluation can cost more than native candidate execution",
    ),
    Probe(
        name="materialized response fallback",
        category="materialization",
        path=ENGINE_SOURCE,
        patterns=(
            r"collect_materialized",
            r"compatibility materialization",
            r"materialized only the requested",
            r"SearchHit",
        ),
        risk="some shapes still require SearchHit materialization boundaries",
    ),
    Probe(
        name="vector/hybrid fallback boundary",
        category="vector-hybrid",
        path=ENGINE_DOC,
        patterns=(
            r"Vector execution is only partially native",
            r"broader vector/hybrid",
            r"fallback",
            r"materialization",
        ),
        risk="unsupported vector/hybrid shapes can fall back to broader materialization",
    ),
    Probe(
        name="mixed shard movement hardening",
        category="mixed-cluster",
        path=PLAN_DOC,
        patterns=(
            r"interrupt Java to SteelSearch recovery",
            r"interrupt SteelSearch primary to Java replica recovery",
            r"retention-lease",
            r"checkpoint monotonicity",
        ),
        risk="representative movement is evidenced, but interruption/resume coverage remains thin",
    ),
    Probe(
        name="checkpoint drift probe",
        category="mixed-cluster",
        path=SHARD_PROBE,
        patterns=(
            r"checkpoint_drift",
            r"checkpoint_drift_ok",
            r"collect_checkpoint_observed",
        ),
        risk="must stay present so mixed movement keeps seq/checkpoint evidence",
    ),
    Probe(
        name="runtime control gaps",
        category="runtime",
        path=RUNTIME_DOC,
        patterns=(
            r"task tracking",
            r"thread-pool",
            r"circuit breaker",
            r"ResourceWatcherService",
        ),
        risk="production load/failure behavior is not fully OpenSearch-equivalent",
    ),
    Probe(
        name="production security fail-closed boundaries",
        category="security",
        path=SECURITY_DOC,
        patterns=(
            r"HTTP TLS",
            r"authentication",
            r"authorization",
            r"audit logging",
            r"fail closed",
        ),
        risk="secure production replacement is blocked until boundaries are enforced",
    ),
)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def probe_result(probe: Probe) -> dict[str, Any]:
    text = read_text(probe.path)
    matches = []
    for pattern in probe.patterns:
        count = len(re.findall(pattern, text, flags=re.IGNORECASE))
        matches.append({"pattern": pattern, "count": count})
    return {
        "name": probe.name,
        "category": probe.category,
        "path": str(probe.path.relative_to(ROOT)),
        "risk": probe.risk,
        "matched": all(item["count"] > 0 for item in matches),
        "matches": matches,
    }


def build_report() -> dict[str, Any]:
    results = [probe_result(probe) for probe in PROBES]
    return {
        "scope": {
            "excluded": [
                "OpenSearch response formatting",
                "OpenSearch snapshot-file compatibility",
                "Lucene segment or translog binary compatibility",
            ],
            "included": [
                "source-backed execution",
                "materialized fallback boundaries",
                "vector/hybrid fallback boundaries",
                "mixed-cluster hardening",
                "production runtime controls",
                "production security enforcement",
            ],
        },
        "summary": {
            "probe_count": len(results),
            "matched_probe_count": sum(1 for result in results if result["matched"]),
            "missing_probe_count": sum(1 for result in results if not result["matched"]),
        },
        "probes": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Non-Native Path Report",
        "",
        "This report excludes format-only OpenSearch parity and direct snapshot or Lucene binary compatibility.",
        "",
        "## Summary",
        "",
        f"- Probes: `{report['summary']['probe_count']}`",
        f"- Matched: `{report['summary']['matched_probe_count']}`",
        f"- Missing: `{report['summary']['missing_probe_count']}`",
        "",
        "## Probes",
        "",
        "| Category | Name | Matched | Source | Risk |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for probe in report["probes"]:
        matched = "yes" if probe["matched"] else "no"
        lines.append(
            f"| {probe['category']} | {probe['name']} | {matched} | `{probe['path']}` | {probe['risk']} |"
        )
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    parser.add_argument("--output")
    args = parser.parse_args()

    report = build_report()
    rendered = (
        json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.format == "json"
        else render_markdown(report)
    )
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if report["summary"]["missing_probe_count"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
