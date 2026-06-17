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
BENCHMARK_MATRIX = ROOT / "tools" / "run-search-benchmark-matrix.py"
NATIVE_CLOSURE_VALIDATION = ROOT / "tools" / "run-native-closure-validation.py"


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
        risk="some shapes still require SearchHit materialization boundaries; benchmark telemetry now exposes the deltas",
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
            r"search_cached_single_index_vector_response",
            r"search_hits_page_for_knn_query_cached",
            r"search_hits_page_for_hybrid_bool_query_cached",
            r"cache_knn_search_result",
            r"request_result_cache_unsupported_vector_bypasses",
            r"request_result_cache_hybrid_vector_bypasses",
            r"search_cache_telemetry_tracks_wired_runtime_cache_surfaces",
        ),
        risk="request-result cache is wired for pure single-index KNN and single-index hybrid bool vector requests with native aggregation/sort plus highlight/explain post-processing; unsupported vector surfaces are counted",
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
        status="native-candidate-narrowed for exact nested term/terms/bool leaves",
        next_action="extend child-ordinal narrowing beyond exact scalar leaves and keep unsupported nested shapes on explicit fallback telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"native_nested_child_ordinals_for_query",
    ),
    Family(
        name="geo_distance query",
        category="source-backed query",
        status="native-candidate-narrowed for geo-point bounding boxes",
        next_action="keep exact circle validation and unsupported geo shapes visible in fallback telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_geo_distance_query",
    ),
    Family(
        name="distance_feature query",
        category="source-backed query",
        status="native-candidate-narrowed for numeric/date field-presence leaves",
        next_action="keep scoring-parity and non-scalar distance_feature shapes visible in fallback telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_distance_feature_query",
    ),
    Family(
        name="rank_feature query",
        category="source-backed query",
        status="native-candidate-narrowed for positive numeric/bool leaves",
        next_action="keep non-scalar rank_feature shapes visible in fallback telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_rank_feature_query",
    ),
    Family(
        name="more_like_this query",
        category="source-backed query",
        status="native-candidate-narrowed for explicit-field token overlap",
        next_action="keep fieldless and analyzer-parity-sensitive more_like_this shapes visible in fallback telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_more_like_this_query",
    ),
    Family(
        name="terms_set query",
        category="source-backed query",
        status="native-candidate-narrowed for exact scalar terms_set leaves",
        next_action="keep complex terms_set fallback visible in materialized telemetry and widen non-scalar coverage only with parity tests",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_minimum_should_match_query",
    ),
    Family(
        name="query_string/simple_query_string",
        category="source-backed query",
        status="native-candidate-narrowed for tokenized text/keyword field sets",
        next_action="keep broad parser, unsupported field-type, and empty-token fallback shapes visible in telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"build_tantivy_tokenized_field_set_query",
    ),
    Family(
        name="materialized SearchHit boundary",
        category="materialization",
        status="present with runtime and benchmark telemetry counters",
        next_action="set closure thresholds and reduce high-delta materialized fallback families",
        evidence_path=BENCHMARK_MATRIX,
        evidence_pattern=r"STEELSEARCH_NATIVE_TELEMETRY_COUNTERS",
    ),
    Family(
        name="malformed wrapper and rebucketing validation",
        category="materialization",
        status="zero-test-guarded compact and rebucketing-wide runtime batches passed",
        next_action="keep malformed-wrapper and rebucketing-wrapper batches in the closure gate while moving remaining work to mixed-cluster, runtime-control, and security evidence",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"REBUCKETING_WIDE_BATCH",
    ),
    Family(
        name="pure knn",
        category="vector-hybrid",
        status="zero-test-guarded vector-knn runtime batch passed",
        next_action="keep unsupported vector/hybrid shapes visible through bypass telemetry and widen only with parity tests",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"VECTOR_KNN_BATCH",
    ),
    Family(
        name="hybrid bool vector path",
        category="vector-hybrid",
        status="direct-path representative coverage including single-index aggregation/sort/cache",
        next_action="keep widening vector coverage using unsupported vector bypass counters",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"search_hits_page_for_hybrid_bool_query_cached",
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
        status="wired for pure single-index KNN and hybrid bool vector requests plus native aggregation/sort/highlight/explain",
        next_action="extend request-result cache coverage beyond the current single-index KNN/hybrid bool vector surface using unsupported-vector bypass telemetry",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"request_result_cache_unsupported_vector_bypasses",
    ),
    Family(
        name="production runtime controls",
        category="runtime",
        status="startup-preflight, startup-readiness, task-cancellation, task-terminal-readback, task-restart-readback, task-queue, route-backpressure, task-throttle, task-parent-metadata, task-header, and same-node task-child grouping batches are zero-test guarded; search/write success, request-error accounting, active-slot queue waiting/drain, bounded queue-full rejection, maintenance route admission, snapshot route admission, cluster-reroute admission, task-submission admission, terminal task readback/pending-depth separation, and task queue/cancelled-id restart readback are runtime-derived, while broader child propagation, terminal retention/eviction, shutdown-window recovery, and multi-node scheduling semantics remain partial",
        next_action="extend task child probes into multi-level/cross-node propagation and route backpressure probes beyond bounded single-node admission into terminal retention/eviction, shutdown-window recovery, and multi-node scheduling behavior",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"task_submission_routes_wait_drain_and_reject_when_runtime_pool_is_saturated",
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
