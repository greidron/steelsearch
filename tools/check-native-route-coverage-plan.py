#!/usr/bin/env python3
"""Validate the planned native-route coverage contract.

This is a preflight checker for tools/fixtures/native-route-coverage-plan.json.
It does not prove runtime readiness. It verifies that the machine-readable plan
has the fields needed by a future native-route coverage runner and that every
known failing family from the current native readiness audit is assigned to at
least one case group.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAN = ROOT / "tools" / "fixtures" / "native-route-coverage-plan.json"

KNOWN_FAILURE_FAMILIES = {
    "bool_query_top_hits",
    "engine_bounds_and_invalidates",
    "grouped_hybrid_bool_index",
    "grouped_hybrid_bool_native",
    "grouped_hybrid_bool_page",
    "hybrid_query_compatibility_leaf",
    "hybrid_query_nested_lexical",
    "hybrid_query_script_sorted",
    "hybrid_query_sorted_compatibility",
    "hybrid_query_supports_alternating",
    "hybrid_query_supports_nested",
    "hybrid_query_supports_scalar",
    "knn_result_cache_is",
    "lexical_mixed_bool_with",
    "lexical_must_not_only",
    "multi_index_hybrid_compatibility",
    "multi_index_hybrid_nested",
    "multi_index_hybrid_script",
    "multi_index_hybrid_sorted",
    "multi_index_hybrid_uses",
    "multi_index_knn_uses",
    "multi_index_native_page",
    "multi_index_native_size",
    "multi_index_plugin_top",
    "multi_index_text_case",
    "multi_index_top_hits",
    "multi_index_vector_native",
    "native_tantivy_terms_and",
    "nested_bool_query_top",
    "non_index_aware_search",
    "script_sort_orders_hits",
    "search_cache_telemetry_tracks",
    "search_populates_distinct_runtime",
    "single_index_grouped_hybrid",
    "single_index_hybrid_script",
    "single_index_knn_uses",
    "single_index_materialized_final",
    "single_index_native_page",
    "single_index_plain_requested",
    "single_index_plain_size",
    "single_index_text_case",
    "single_index_vector_native",
    "stale_knn_cache_drops",
}


def error(message: str) -> dict[str, str]:
    return {"level": "error", "message": message}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        raise SystemExit(f"plan file not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"invalid JSON in {path}: {exc}") from None


def require_bool(value: Any, field: str, issues: list[dict[str, str]]) -> None:
    if not isinstance(value, bool):
        issues.append(error(f"{field} must be a boolean"))


def require_string_list(value: Any, field: str, issues: list[dict[str, str]]) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        issues.append(error(f"{field} must be a list of strings"))


def validate_plan(plan: Any) -> tuple[list[dict[str, str]], dict[str, Any]]:
    issues: list[dict[str, str]] = []
    if not isinstance(plan, dict):
        return [error("plan root must be an object")], {}

    if plan.get("schema_version") != 1:
        issues.append(error("schema_version must be 1"))
    if not isinstance(plan.get("name"), str) or not plan["name"]:
        issues.append(error("name must be a non-empty string"))

    gate = plan.get("readiness_gate")
    if not isinstance(gate, dict):
        issues.append(error("readiness_gate must be an object"))
    else:
        for field in [
            "requires_opensearch_visible_parity",
            "requires_steelsearch_native_route_evidence",
            "requires_no_compatibility_fallback",
            "requires_no_top_level_hit_materialization_when_size_zero",
        ]:
            require_bool(gate.get(field), f"readiness_gate.{field}", issues)

    case_groups = plan.get("case_groups")
    if not isinstance(case_groups, list) or not case_groups:
        issues.append(error("case_groups must be a non-empty list"))
        case_groups = []

    covered: set[str] = set()
    group_names: set[str] = set()
    native_requirement_keys: set[str] = set()
    opensearch_query_families = 0
    opensearch_variants = 0

    for index, group in enumerate(case_groups):
        prefix = f"case_groups[{index}]"
        if not isinstance(group, dict):
            issues.append(error(f"{prefix} must be an object"))
            continue

        name = group.get("name")
        if not isinstance(name, str) or not name:
            issues.append(error(f"{prefix}.name must be a non-empty string"))
        elif name in group_names:
            issues.append(error(f"duplicate case group name: {name}"))
        else:
            group_names.add(name)

        families = group.get("failure_families")
        require_string_list(families, f"{prefix}.failure_families", issues)
        if isinstance(families, list):
            covered.update(item for item in families if isinstance(item, str))

        parity = group.get("opensearch_parity")
        if not isinstance(parity, dict):
            issues.append(error(f"{prefix}.opensearch_parity must be an object"))
        else:
            require_string_list(parity.get("indices"), f"{prefix}.opensearch_parity.indices", issues)
            require_string_list(
                parity.get("query_families"),
                f"{prefix}.opensearch_parity.query_families",
                issues,
            )
            require_string_list(parity.get("variants"), f"{prefix}.opensearch_parity.variants", issues)
            if isinstance(parity.get("query_families"), list):
                opensearch_query_families += len(parity["query_families"])
            if isinstance(parity.get("variants"), list):
                opensearch_variants += len(parity["variants"])

        native = group.get("steelsearch_native_requirements")
        if not isinstance(native, dict) or not native:
            issues.append(error(f"{prefix}.steelsearch_native_requirements must be a non-empty object"))
        else:
            native_requirement_keys.update(native.keys())
            for key, value in native.items():
                if key.endswith("descriptions") or key.endswith("substrings"):
                    require_string_list(value, f"{prefix}.steelsearch_native_requirements.{key}", issues)
                elif key.startswith("requires_"):
                    require_bool(value, f"{prefix}.steelsearch_native_requirements.{key}", issues)

    unknown = sorted(covered - KNOWN_FAILURE_FAMILIES)
    missing = sorted(KNOWN_FAILURE_FAMILIES - covered)
    for family in unknown:
        issues.append(error(f"unknown failure family in plan: {family}"))
    for family in missing:
        issues.append(error(f"known failure family is not covered by plan: {family}"))

    summary = {
        "case_group_count": len(case_groups),
        "known_failure_family_count": len(KNOWN_FAILURE_FAMILIES),
        "covered_failure_family_count": len(covered & KNOWN_FAILURE_FAMILIES),
        "missing_failure_families": missing,
        "unknown_failure_families": unknown,
        "native_requirement_keys": sorted(native_requirement_keys),
        "opensearch_query_family_entries": opensearch_query_families,
        "opensearch_variant_entries": opensearch_variants,
    }
    return issues, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=DEFAULT_PLAN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    plan = load_json(args.plan)
    issues, summary = validate_plan(plan)
    report = {
        "plan": str(args.plan),
        "ok": not issues,
        "summary": summary,
        "issues": issues,
    }

    text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n")
    else:
        print(text)

    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
