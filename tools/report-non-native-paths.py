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
            r"source-backed `match_phrase`",
            r"source-backed `match_phrase_prefix`",
            r"source-backed `match_bool_prefix`",
            r"source-backed `multi_match`",
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
            r"checkpoint_monotonicity_ok",
            r"unsupported_allocation_explain_ok",
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
            r"checkpoint_monotonicity_ok",
            r"retention_lease_metadata_ok",
            r"collect_retention_leases_observed",
            r"unsupported_allocation_explain_ok",
            r"capture_unsupported_allocation_explain",
            r"collect_checkpoint_observed",
            r"interruption_evidence_passed",
            r"--require-interruption",
            r"--exercise-interruption",
            r"interrupt_java_to_steelsearch_recovery",
            r"interrupt_steelsearch_to_opensearch_recovery",
        ),
        risk="must stay present so mixed movement keeps seq/checkpoint drift, monotonicity, retention-lease metadata, and unsupported allocation-explain evidence, the interrupted/resumed phase contract, the enforceable gate option, and both live interruption exercises",
    ),
    Probe(
        name="mixed shard movement validation batch",
        category="mixed-cluster",
        path=NATIVE_CLOSURE_VALIDATION,
        patterns=(
            r"MIXED_SHARD_MOVEMENT_BATCH",
            r"mixed-shard-movement",
            r"--exercise-interruption",
            r"--require-interruption",
        ),
        risk="must stay wired so the final mixed-cluster gate can run the live interruption probe",
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
            r"multi_index_knn_vector_cache_populates_request_result_cache_detail_entries",
            r"multi_index_hybrid_vector_request_result_cache_is_telemetry_visible",
        ),
        risk="request-result cache is wired for pure single-index and multi-index KNN plus hybrid bool vector requests with native aggregation/sort plus highlight/explain post-processing and same-request refresh correctness; unsupported non-vector-score cache surfaces remain telemetry-counted",
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
        name="module and feature registration boundaries",
        category="runtime",
        path=RUNTIME_DOC,
        patterns=(
            r"module-registration",
            r"extension manifest",
            r"_cat/plugins",
            r"startup transcript",
            r"Rust-native feature registration",
        ),
        risk="runtime feature/module loading must be visible and registry-derived rather than implied by compiled-in route stubs",
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
            r"security audit events",
            r"fail closed",
            r"OpenSearch Security plugin API",
        ),
        risk="secure production replacement is blocked until boundaries are enforced; baseline audit events and unsupported OpenSearch Security plugin API fail-closed behavior are now explicit",
    ),
)

FAMILIES: tuple[Family, ...] = (
    Family(
        name="nested query",
        category="source-backed query",
        status="native-candidate-narrowed for exact nested term/terms/terms_set/range/exists/rank_feature/prefix/wildcard/regexp/fuzzy/match/match_phrase/match_phrase_prefix/match_bool_prefix/bool leaves",
        next_action="keep unsupported nested shapes on explicit fallback telemetry while using child-ordinal narrowing for the current safe scalar, rank-feature, terms-set, match, phrase, bool-prefix, and string-pattern leaves",
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
        next_action="keep analyzer-parity-sensitive more_like_this shapes visible in fallback telemetry while fieldless source-candidate native page coverage stays guarded",
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
        name="phrase/bool-prefix/multi_match query",
        category="source-backed query",
        status="native-candidate-narrowed for match_phrase, match_phrase_prefix, match_bool_prefix, and multi_match explicit-field subsets",
        next_action="keep analyzer-sensitive and broad multi-field parser shapes visible in fallback telemetry",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"grouped_hybrid_bool_multi_match_leaf_reduces_candidate_ids_directly",
    ),
    Family(
        name="source-backed query validation gate",
        category="source-backed query",
        status="zero-test-guarded source-backed-query batch passed for current native execution, explicit fallback-boundary source validation, and hybrid candidate-reduction surfaces",
        next_action="keep the source-backed-query batch in the closure gate while widening only with parity tests and fallback telemetry",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"SOURCE_BACKED_QUERY_BATCH",
    ),
    Family(
        name="materialized SearchHit boundary",
        category="materialization",
        status="present with zero-test-guarded benchmark/load telemetry for materialized fetches, avoided materialization, compatibility materialization, request-result cache bypass causes, per-success materialization budget pass/fail rows for materialized and compatibility materialized response fetches, opt-in operation-level native counter deltas for exact single-client materialization attribution, ranked materialization-priority reports from operation-resource-delta slices, a fresh Steelsearch diagnostic harness for generating load and priority artifacts, opt-in fallback diagnostic workloads for query_string, terms_set, distance_feature, rank_feature, more_like_this, and case-insensitive wildcard, HTTP query_string native-path stats wiring that exposes compatibility materialization through _nodes/stats, query_string/simple_query_string plus distance_feature, rank_feature, terms_set, fieldless more_like_this, and text-field case-insensitive wildcard source-candidate native page paths, and targeted matrix evidence that fallback_distance_feature, fallback_rank_feature, fallback_terms_set, fallback_more_like_this, and fallback_case_insensitive_wildcard now report zero materialized and compatibility materialized response fetches; latest targeted priority report passes with ranked_operation_count=0",
        next_action="keep the targeted materialization-priority matrix at ranked_operation_count=0 while widening only with parity tests and operation-level telemetry",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"BENCHMARK_TELEMETRY_BATCH|rank-materialization-priorities|run-materialization-priority-diagnostic",
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
        status="zero-test-guarded vector-knn runtime batch passed with pure KNN and hybrid vector-native page/aggregation/sort coverage plus single-index and multi-index request-result cache telemetry",
        next_action="keep unsupported vector/hybrid shapes visible through fallback telemetry while widening only with parity tests",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"VECTOR_KNN_BATCH",
    ),
    Family(
        name="hybrid bool vector path",
        category="vector-hybrid",
        status="direct-path representative coverage including single-index aggregation/sort/cache",
        next_action="keep widening vector coverage using explicit fallback counters for unsupported shapes",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"search_hits_page_for_hybrid_bool_query_cached",
    ),
    Family(
        name="mixed shard movement interruption",
        category="mixed-cluster",
        status="mixed-shard validation batch passed with both-direction live interruption exercises, zero checkpoint drift, checkpoint monotonicity, retention-lease metadata, and unsupported movement allocation-explain evidence",
        next_action="keep the mixed-shard movement batch in the release gate and move remaining non-native closure work to runtime fairness and production security",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"mixed-shard-movement",
    ),
    Family(
        name="runtime search cache hooks",
        category="runtime",
        status="wired for pure single-index and multi-index KNN plus hybrid bool vector requests with native aggregation/sort/highlight/explain, refresh-correct per-index cache invalidation, and telemetry for unsupported non-vector-score cache surfaces",
        next_action="keep widening cache coverage only where the native cache key preserves request semantics and index-local invalidation",
        evidence_path=ENGINE_SOURCE,
        evidence_pattern=r"multi_index_knn_vector_cache_populates_request_result_cache_detail_entries",
    ),
    Family(
        name="production runtime controls",
        category="runtime",
        status="startup-preflight, startup-readiness, task-cancellation, task-cancel-idempotency, task-terminal-readback, task-restart-readback, task-queue, route-backpressure, runtime-fairness, task-throttle, task-parent-metadata, task-header, and task-child grouping/cancellation/rethrottle batches are zero-test guarded; explicit OpenSearch -E config-setting rejection, missing/readonly/locked/file-backed data-path preflight checks, readiness terminology smoke coverage, search/write success, request-error accounting, active-slot queue waiting/drain, independent mixed search/maintenance and write/maintenance backlog drain, remote task backlog admission isolation for task-submission and local search/write routes, bounded queue-full rejection, maintenance route admission, snapshot route admission, cluster-reroute admission, task-submission admission, accepted queued task-submission no-replay across shared-runtime restart and partial shared-state recovery errors, partial-recovery task-submission refusal, live-shutdown task-submission refusal, runtime thread-pool queue/counter restart reset, repeated cancel idempotency, parent-task-id child cancellation visibility, same-node, cross-node, and background-worker descendant cancellation propagation, queued-versus-in-flight cancellation visibility, active queued/in-flight node-role-transition cancellation/refusal, multi-node queued/in-flight task visibility with remote node metadata, node-specific cat thread-pool management telemetry, node-scoped cat thread-pool control-plane telemetry under remote backlog, simulated multi-node local overload counter isolation from remote task metadata, restarted three-daemon remote-backlog telemetry with transport keepalive reachability plus local search/write admission, TCP shard-search and replica-operation transport execution slices, bounded shard-search transport queue drain/reject behavior exposed through node-stats and cat thread-pool remote_transport telemetry, live daemon query-phase transport route admission through the shared remote transport queue gate, live three-daemon TCP query-phase stress with queue rejection plus REST telemetry readback, and OpenSearch peer comparison showing analogous search thread-pool rejection/readback under equivalent query pressure with an explicit mixed Java/Rust query-phase profile contract, completion-race terminal refusal without cancelled-marker pollution, repeated rethrottle last-write-wins readback, throttle-rate restart readback, cancel/rethrottle per-request sync-on-restart mutation, accepted in-flight task restart readback/refusal without queued replay, partial shared-state recovery error task-listing/cancel continuity, cancelled-terminal restart-sync, live-shutdown, and node-role-transition refusal with progress preservation, cancelled/terminal rethrottle refusal, same-node parent/child and multi-level independent rethrottle rate readback, terminal task readback/pending-depth separation, acknowledged/failed terminal retention/eviction restart readback, stale cancellation-marker pruning for evicted terminal tasks, cancelled-task completion and partial-progress status readback through restart until eviction, and task queue/cancelled-id restart readback are runtime-derived",
        next_action="run the optional live mixed-cluster coordinator/receiver peer-backpressure track when a Java coordinator can drive Rust query-phase transport directly",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"RUNTIME_(FAIRNESS|PEER_BACKPRESSURE)_BATCH",
    ),
    Family(
        name="module registration boundaries",
        category="runtime",
        status="module-registration batch is zero-test guarded; extension manifest booleans feed the effective runtime registry, malformed manifests and unsupported Java plugin ABI manifests fail closed, formal Rust-native extension API descriptors from owning crates feed registry-derived route/action/module/lifecycle-hook registration tables and startup transcript output per profile, Steelsearch runtime exposes startup/restart sync, task-admission, live-shutdown, and partial-recovery lifecycle hook names while compatibility-only k-NN and ML Commons descriptors expose none, local SteelNode activation, shutdown deactivation, and recovery-failed transitions execute registered lifecycle hook names and record a runtime transcript, _cat/plugins reports registry-enabled Steelsearch runtime, k-NN, and ML Commons module rows while omitting disabled modules, and a live three-daemon development cluster exposes the enabled module rows plus startup/steady-state and shutdown/recovery lifecycle transition transcripts through the runtime dev extension surface on every node",
        next_action="keep module-registration in the closure gate while moving remaining native-closure work to runtime fairness, materialization budget, cache-key expansion, and production security controls",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"MODULE_REGISTRATION_BATCH",
    ),
    Family(
        name="production security",
        category="security",
        status="structured fail-closed boundary/checklist gate with distinct HTTP TLS and transport TLS blockers, REST HTTP TLS listener enforcement with rustls certificate/key loading and production policy promotion, transport seed listener TLS enforcement with rustls certificate/key loading, transport-frame read/write over TLS, and production policy promotion, runtime-security/authn-bootstrap driven production policy promotion for authentication, authorization, audit logging, and tenant isolation when bootstrap subjects carry tenant scopes, secure-settings-file bootstrap validation with production policy promotion, artifact-backed release-readiness evidence-file input with complete-evidence production startup acceptance and invalid/missing-artifact fail-closed coverage, release-readiness attachment tooling that writes the five-artifact production startup manifest from benchmark/load/chaos/packaging/rolling-upgrade reports, PEM-marker TLS, certificate/private-key role mismatch rejection, invalid bootstrap file-content redaction, guarded secure multi-node TLS handshake matrix buckets, authn bootstrap material preflight, production startup refusal unless STEELSEARCH_SECURITY_ENABLED=true enables runtime security enforcement, shared users/service-account subject parser with service-account-only authentication-users-file acceptance and malformed authentication-users-file rejection, runtime env credential loading through that subject model including tenant scopes, shared admin/reader/writer permission evaluator, guarded root/ML/bulk/search/session authn/authz checks, tenant-scoped same-tenant read/write allow and cross-tenant read/write/bulk denial, service-account writer authz, single-document read/write role checks, multi-document/document-analysis read role checks, cluster observability reader-route checks, reindex/delete-by-query/update-by-query writer-route checks, secure-settings reload admin-role enforcement, cluster-admin control route enforcement for settings/reroute/decommission, weighted routing, voting config exclusions, snapshot mutation/control routes, template management mutation routes, search/ingest pipeline management routes, stored script management routes, data stream management/rollover routes, alias metadata mutation routes with bulk/named mutation lock-reentry removed, index settings/mapping mutation routes with empty mapping-property update panic removed, index metadata read route checks, index maintenance open/close/cache controls with closed-index reopen resolution, index structure delete/block/resize controls plus root index create/read routes, k-NN settings/model/cache mutation routes, dangling-index/remote-store recovery mutation routes, ingestion pause/resume control routes, and task cancel/rethrottle surfaces, bounded security audit event persistence including permission-evaluator read/write denials and multi-route OpenSearch Security plugin API fail-closed decisions without request-secret persistence, ML connector secret redaction from REST responses and shared runtime persistence, and explicit OpenSearch Security plugin API fail-closed responses",
        next_action="run final benchmark, load, chaos, packaging, and rolling-upgrade evidence capture before production cutover and feed those artifacts through the release-readiness manifest writer",
        evidence_path=NATIVE_CLOSURE_VALIDATION,
        evidence_pattern=r"PRODUCTION_SECURITY_BATCH",
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
                "module/feature registration boundaries",
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
