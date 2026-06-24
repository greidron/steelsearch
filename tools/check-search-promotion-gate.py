#!/usr/bin/env python3
"""Validate search promotion gate coverage."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "fixture",
        nargs="?",
        default="tools/fixtures/search-promotion-gate.json",
    )
    return parser.parse_args()


def ensure_subset(name: str, actual: list[str], required: set[str]) -> None:
    missing = sorted(required - set(actual))
    if missing:
        raise SystemExit(f"{name} missing required entries: {missing}")


def main() -> int:
    args = parse_args()
    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))

    if fixture.get("source_area") != "REST `_search`":
        raise SystemExit("search promotion gate fixture has the wrong source_area")
    if fixture.get("profile") != "standalone":
        raise SystemExit("search promotion gate must target the standalone profile")

    expectation = fixture.get("matrix_expectation") or {}
    if expectation.get("open_search_api_compatibility") != "Implemented":
        raise SystemExit("search promotion expects OpenSearch API compatibility = Implemented")
    if expectation.get("production_readiness") != "Yes":
        raise SystemExit("search promotion expects Production readiness = Yes")

    sections = fixture.get("unified_report_sections") or {}
    for section_name in ("route_parity", "semantic_parity", "security_parity"):
        if section_name not in sections:
            raise SystemExit(f"missing unified report section: {section_name}")

    route = sections["route_parity"]
    semantic = sections["semantic_parity"]
    security = sections["security_parity"]

    ensure_subset(
        "route_parity.required_suites",
        route.get("required_suites") or [],
        {"common-baseline", "search-execution"},
    )
    ensure_subset(
        "route_parity.report_paths",
        route.get("report_paths") or [],
        {"search-compat-report.json"},
    )
    ensure_subset(
        "semantic_parity.required_cases",
        semantic.get("required_cases") or [],
        {
            "exists_query_search",
            "validate_query_empty_search",
            "validate_query_target_rewrite_search",
            "match_query_scoring_order_total_hits",
            "prefix_query_search",
            "query_string_search",
            "query_string_url_q_overrides_body_search",
            "count_query_string_url_q_search",
            "render_template_named_search",
            "search_template_named_target_search",
            "msearch_template_named_root_search",
            "regexp_query_search",
            "terms_set_query_search",
            "wildcard_query_search",
            "nested_query_search",
            "rank_eval_precision_search",
            "pit_open_search",
            "pit_list_search",
            "pit_clear_all_search",
            "pit_clear_all_body_search",
            "pit_search_after_close_missing_context",
            "pit_search",
            "pit_search_extends_keep_alive",
            "pit_search_with_routing_filter",
            "pit_snapshot_after_update_delete_search",
            "pit_search_with_default_ignore_throttled",
            "pit_search_with_order_sensitive_default_wildcards",
            "pit_search_with_default_ccs_minimize_roundtrips",
            "scroll_initial_search",
            "scroll_follow_up_search",
            "search_after_search",
            "collapse_search",
            "profile_search",
            "rescore_search",
            "function_score_search",
            "script_score_search",
            "search_coordinator_knobs_search",
            "allow_partial_search_results_true_search",
            "track_scores_field_sort_search",
            "completion_suggest_search",
            "phrase_suggest_search",
            "term_suggest_search",
            "highlight_search",
            "metric_aggregations",
            "filter_aggregations",
            "terms_aggregation",
            "composite_aggregation",
            "geo_bounds_aggregation",
            "sum_bucket_pipeline_aggregation",
            "scripted_metric_aggregation",
            "partial_shard_failure_geo_search",
            "allow_partial_search_results_execution_summary",
            "expand_wildcards_closed_fail_closed",
        },
    )
    ensure_subset(
        "security_parity.report_paths",
        security.get("report_paths") or [],
        {"security-authz-compat-report.json"},
    )
    ensure_subset(
        "security_parity.required_cases",
        security.get("required_cases") or [],
        {
            "security_reader_root_search_success",
            "security_missing_target_search_401",
            "security_writer_root_search_403",
        },
    )

    deny = fixture.get("unsupported_option_deny_ledger") or {}
    if deny.get("fixture") != "search-unsupported-option-deny-ledger.json":
        raise SystemExit("search promotion gate must point at search-unsupported-option-deny-ledger.json")
    ensure_subset(
        "unsupported_option_deny_ledger.required_cases",
        deny.get("required_cases") or [],
        {
            "runtime_mappings_request_body_fail_closed",
        },
    )

    gate = fixture.get("latest_standalone_gate") or {}
    ensure_subset(
        "latest_standalone_gate.required_entrypoints",
        gate.get("required_entrypoints") or [],
        {
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope search",
            "tools/run-phase-a-acceptance-harness.sh --mode local --scope search-execution",
            "tools/run-security-compat-harness.sh --profile single-node-secure",
        },
    )
    ensure_subset(
        "latest_standalone_gate.required_reports",
        gate.get("required_reports") or [],
        {"search-compat-report.json", "security-authz-compat-report.json"},
    )

    print(
        json.dumps(
            {
                "fixture": str(Path(args.fixture)),
                "profile": fixture["profile"],
                "source_area": fixture["source_area"],
                "status": "ok",
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
