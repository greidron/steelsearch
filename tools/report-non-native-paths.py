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


@dataclass(frozen=True)
class Family:
    name: str
    category: str
    status: str
    next_action: str
    evidence_path: Path
    evidence_pattern: str


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
            r"materialized_response_fetches",
            r"compatibility_materialized_response_fetches",
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
        path=ENGINE_SOURCE,
        patterns=(
            r"search_cached_single_index_knn_response",
            r"search_hits_page_for_knn_query_cached",
            r"cache_knn_search_result",
            r"search_cache_telemetry_tracks_wired_runtime_cache_surfaces",
        ),
        risk="request-result cache is wired for pure single-index KNN with native aggregation/sort, but highlight/explain and hybrid vector combinations still bypass it",
    ),
    Probe(
        name="production runtime controls",
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

FAMILIES: tuple[Family, ...] = (
    Family(
        name="nested query",
        category="source-backed query",
        status="source-backed",
        next_action="add candidate narrowing before source evaluation for common nested scalar/text leaves",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `nested`",
    ),
    Family(
        name="geo_distance query",
        category="source-backed query",
        status="source-backed",
        next_action="evaluate whether geo-point index data can avoid full source scan for bounded distance filters",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `geo_distance`",
    ),
    Family(
        name="distance_feature query",
        category="source-backed query",
        status="source-backed",
        next_action="promote numeric/date candidate narrowing if scoring parity is preserved",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `distance_feature`",
    ),
    Family(
        name="rank_feature query",
        category="source-backed query",
        status="source-backed",
        next_action="promote positive numeric/bool feature lookup away from broad source evaluation",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `rank_feature`",
    ),
    Family(
        name="more_like_this query",
        category="source-backed query",
        status="source-backed",
        next_action="replace token-overlap source pass with indexed-term candidate path where analyzer parity is known",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `more_like_this`",
    ),
    Family(
        name="terms_set query",
        category="source-backed query",
        status="source-backed",
        next_action="split scalar exact-match candidate narrowing from minimum-match source fallback",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `terms_set`",
    ),
    Family(
        name="query_string/simple_query_string",
        category="source-backed query",
        status="source-backed broad parser fallback",
        next_action="separate simple fielded terms from broad default-field source-derived clauses",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"source-backed `query_string`",
    ),
    Family(
        name="materialized SearchHit boundary",
        category="materialization",
        status="present with telemetry counters",
        next_action="feed materialized response counters into benchmark summaries and closure thresholds",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"materialized_response_fetches",
    ),
    Family(
        name="pure knn",
        category="vector-hybrid",
        status="partially native",
        next_action="keep direct vector path covered while adding unsupported-shape counters",
        evidence_path=ENGINE_DOC,
        evidence_pattern=r"top-level `knn` queries use the engine direct vector path",
    ),
    Family(
        name="hybrid bool vector path",
        category="vector-hybrid",
        status="direct-path representative coverage including single-index aggregation/sort",
        next_action="add unsupported-shape counters and extend hybrid request-result cache coverage",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"single_index_hybrid_uses_vector_native_page_and_aggregation_fetch_with_fast_field_sort",
    ),
    Family(
        name="mixed shard movement interruption",
        category="mixed-cluster",
        status="planned",
        next_action="add interrupted and resumed recovery phases to the live shard movement probe",
        evidence_path=PLAN_DOC,
        evidence_pattern=r"interrupt Java to SteelSearch recovery",
    ),
    Family(
        name="runtime search cache hooks",
        category="runtime",
        status="wired for pure single-index KNN plus native aggregation/sort",
        next_action="extend request-result cache coverage to highlight, explain, and hybrid vector combinations",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"search_hits_page_for_knn_query_cached",
    ),
    Family(
        name="production runtime controls",
        category="runtime",
        status="partial",
        next_action="start with startup refusal and task registry probes",
        evidence_path=RUNTIME_DOC,
        evidence_pattern=r"Thread Pools, Task Tracking, And Runtime Controls",
    ),
    Family(
        name="production security",
        category="security",
        status="fail-closed",
        next_action="start with TLS/authn bootstrap fixtures before enabling production startup",
        evidence_path=SECURITY_DOC,
        evidence_pattern=r"Production security readiness requires",
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


def family_result(family: Family) -> dict[str, Any]:
    text = read_text(family.evidence_path)
    count = len(re.findall(family.evidence_pattern, text, flags=re.IGNORECASE))
    return {
        "name": family.name,
        "category": family.category,
        "status": family.status,
        "next_action": family.next_action,
        "evidence_path": str(family.evidence_path.relative_to(ROOT)),
        "evidence_pattern": family.evidence_pattern,
        "evidence_count": count,
        "evidenced": count > 0,
    }


def build_report() -> dict[str, Any]:
    results = [probe_result(probe) for probe in PROBES]
    families = [family_result(family) for family in FAMILIES]
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
            "family_count": len(families),
            "evidenced_family_count": sum(1 for family in families if family["evidenced"]),
            "missing_family_count": sum(1 for family in families if not family["evidenced"]),
        },
        "probes": results,
        "families": families,
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
        f"- Families: `{report['summary']['family_count']}`",
        f"- Evidenced families: `{report['summary']['evidenced_family_count']}`",
        f"- Missing families: `{report['summary']['missing_family_count']}`",
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
    lines.extend(
        [
            "",
            "## Family Inventory",
            "",
            "| Category | Family | Status | Evidenced | Next action |",
            "| --- | --- | --- | ---: | --- |",
        ]
    )
    for family in report["families"]:
        evidenced = "yes" if family["evidenced"] else "no"
        lines.append(
            f"| {family['category']} | {family['name']} | {family['status']} | {evidenced} | {family['next_action']} |"
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
    missing = report["summary"]["missing_probe_count"] + report["summary"]["missing_family_count"]
    return 0 if missing == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
