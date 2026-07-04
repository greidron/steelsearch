#!/usr/bin/env python3
"""Validate source compatibility matrix covers every generated source inventory row."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GENERATED = ROOT / "docs/rust-port/generated"
DEFAULT_MATRIX = DEFAULT_GENERATED / "source-compatibility-matrix.tsv"
DEFAULT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"
SOURCE_FILES = {
    "rest_route": DEFAULT_GENERATED / "source-rest-routes.tsv",
    "transport_action": DEFAULT_GENERATED / "source-transport-actions.tsv",
    "search_registration": DEFAULT_GENERATED / "source-search-registrations.tsv",
    "node_runtime": DEFAULT_GENERATED / "source-node-runtime-components.tsv",
}
VALID_STATUSES = {"implemented", "out-of-scope", "partial", "planned"}
VALID_CATEGORIES = {
    "node_runtime": {"controller", "module", "registry", "service"},
    "rest_route": {"", "DELETE", "GET", "HEAD", "POST", "PUT"},
    "search_registration": {
        "aggregation",
        "fetch_subphase",
        "pipeline_aggregation",
        "query",
        "score_function",
        "suggester",
    },
    "transport_action": {"action"},
}
REQUIRED_MATRIX_FIELDS = ("surface", "status", "category", "identifier", "detail", "source", "line")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--generated-dir", type=Path, default=DEFAULT_GENERATED)
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def validate_matrix(
    matrix_path: Path,
    generated_dir: Path,
    runtime_source: Path = DEFAULT_RUNTIME_SOURCE,
) -> dict[str, object]:
    matrix_rows = read_rows(matrix_path)
    expected_rows = expected_matrix_rows(generated_dir)
    matrix_keys = row_keys(matrix_rows)
    expected_keys = row_keys(expected_rows)
    duplicate_matrix_rows = duplicates(matrix_rows)
    duplicate_expected_rows = duplicates(expected_rows)
    missing = sorted(expected_keys - matrix_keys)
    extra = sorted(matrix_keys - expected_keys)
    errors = taxonomy_errors(matrix_rows)
    if duplicate_matrix_rows:
        errors.append(f"matrix has duplicate rows: {duplicate_matrix_rows[:10]}")
    if duplicate_expected_rows:
        errors.append(f"source inventories project duplicate matrix rows: {duplicate_expected_rows[:10]}")
    if missing:
        errors.append(f"matrix is missing source inventory rows: {missing[:10]}")
    if extra:
        errors.append(f"matrix has rows outside source inventories: {extra[:10]}")
    missing_transport_anchor_surface = transport_action_source_anchor_surface_missing(
        runtime_source
    )
    missing_rest_anchor_surface = rest_route_source_anchor_surface_missing(runtime_source)
    missing_source_inventory_summary = source_inventory_summary_surface_missing(
        runtime_source
    )
    missing_source_partial_readiness = source_partial_readiness_surface_missing(
        runtime_source
    )
    if missing_transport_anchor_surface:
        errors.append(
            "runtime source is missing transport action source-anchor surface: "
            f"{missing_transport_anchor_surface}"
        )
    if missing_rest_anchor_surface:
        errors.append(
            "runtime source is missing REST route source-anchor surface: "
            f"{missing_rest_anchor_surface}"
        )
    if missing_source_inventory_summary:
        errors.append(
            "runtime source is missing source inventory summary surface: "
            f"{missing_source_inventory_summary}"
        )
    if missing_source_partial_readiness:
        errors.append(
            "runtime source is missing source partial promotion readiness surface: "
            f"{missing_source_partial_readiness}"
        )
    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "matrix_row_count": len(matrix_rows),
            "expected_row_count": len(expected_rows),
            "missing_row_count": len(missing),
            "extra_row_count": len(extra),
            "duplicate_matrix_row_count": len(duplicate_matrix_rows),
            "duplicate_expected_row_count": len(duplicate_expected_rows),
            "status_counts": status_counts(matrix_rows),
            "surface_counts": surface_counts(matrix_rows),
            "missing_transport_anchor_surface_count": len(
                missing_transport_anchor_surface
            ),
            "missing_rest_anchor_surface_count": len(missing_rest_anchor_surface),
            "missing_source_inventory_summary_count": len(
                missing_source_inventory_summary
            ),
            "missing_source_partial_readiness_count": len(
                missing_source_partial_readiness
            ),
        },
    }


def transport_action_source_anchor_surface_missing(runtime_source: Path) -> list[str]:
    text = runtime_source.read_text(encoding="utf-8")
    required_tokens = {
        "generated TSV include": (
            'include_str!("../../../docs/rust-port/generated/source-transport-actions.tsv")'
        ),
        "source anchor struct": "pub struct TransportActionSourceAnchor",
        "source anchor status field": "pub status: String",
        "source anchor action field": "pub action: String",
        "source anchor transport handler field": "pub transport_handler: String",
        "source anchor source field": "pub source: String",
        "source anchor line field": "pub line: u32",
        "source anchor function": "pub fn transport_action_source_anchors()",
        "dev endpoint key": '"transport_action_source_anchors": transport_action_source_anchors()',
    }
    return [label for label, token in required_tokens.items() if token not in text]


def rest_route_source_anchor_surface_missing(runtime_source: Path) -> list[str]:
    text = runtime_source.read_text(encoding="utf-8")
    required_tokens = {
        "generated TSV include": (
            'include_str!("../../../docs/rust-port/generated/source-rest-routes.tsv")'
        ),
        "source anchor struct": "pub struct RestRouteSourceAnchor",
        "source anchor status field": "pub status: String",
        "source anchor method field": "pub method: String",
        "source anchor path field": "pub path_or_expression: String",
        "source anchor source field": "pub source: String",
        "source anchor line field": "pub line: u32",
        "source anchor function": "pub fn rest_route_source_anchors()",
        "dev endpoint key": '"rest_route_source_anchors": rest_route_source_anchors()',
    }
    return [label for label, token in required_tokens.items() if token not in text]


def source_inventory_summary_surface_missing(runtime_source: Path) -> list[str]:
    text = runtime_source.read_text(encoding="utf-8")
    required_tokens = {
        "summary struct": "pub struct SourceInventorySummary",
        "summary surface field": "pub surface: &'static str",
        "summary row count field": "pub row_count: usize",
        "summary implemented field": "pub implemented: usize",
        "summary partial field": "pub partial: usize",
        "summary out of scope field": "pub out_of_scope: usize",
        "summary planned field": "pub planned: usize",
        "summary function": "pub fn source_inventory_summaries()",
        "dev endpoint key": '"source_inventory_summary": source_inventory_summaries()',
    }
    return [label for label, token in required_tokens.items() if token not in text]


def source_partial_readiness_surface_missing(runtime_source: Path) -> list[str]:
    text = runtime_source.read_text(encoding="utf-8")
    required_tokens = {
        "readiness JSON include": (
            'include_str!("../../../tools/fixtures/source-partial-promotion-readiness.json")'
        ),
        "readiness function": "pub fn source_partial_promotion_readiness() -> Value",
        "readiness name": '"name": "source-partial-promotion-readiness"',
        "dev endpoint key": '"source_partial_promotion_readiness": source_partial_promotion_readiness()',
        "readiness summary function": "pub fn source_partial_promotion_summary() -> Value",
        "readiness summary endpoint key": '"source_partial_promotion_summary": source_partial_promotion_summary()',
    }
    return [label for label, token in required_tokens.items() if token not in text]


def expected_matrix_rows(generated_dir: Path) -> list[dict[str, str]]:
    return [
        *project_rest_routes(read_rows(generated_dir / "source-rest-routes.tsv")),
        *project_transport_actions(read_rows(generated_dir / "source-transport-actions.tsv")),
        *project_search_registrations(read_rows(generated_dir / "source-search-registrations.tsv")),
        *project_node_runtime(read_rows(generated_dir / "source-node-runtime-components.tsv")),
    ]


def project_rest_routes(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "surface": "rest_route",
            "status": row["status"],
            "category": row["method"],
            "identifier": row["path_or_expression"],
            "detail": "",
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
    ]


def project_transport_actions(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "surface": "transport_action",
            "status": row["status"],
            "category": "action",
            "identifier": row["action"],
            "detail": row["transport_handler"],
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
    ]


def project_search_registrations(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "surface": "search_registration",
            "status": row["status"],
            "category": row["category"],
            "identifier": row["expression"],
            "detail": "",
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
    ]


def project_node_runtime(rows: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    return [
        {
            "surface": "node_runtime",
            "status": row["status"],
            "category": row["kind"],
            "identifier": row["component"],
            "detail": "",
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
    ]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def row_keys(rows: Iterable[dict[str, str]]) -> set[tuple[str, str, str, str, str, str, str]]:
    return {
        (
            row["surface"],
            row["status"],
            row["category"],
            row["identifier"],
            row["detail"],
            row["source"],
            row["line"],
        )
        for row in rows
    }


def duplicates(rows: list[dict[str, str]]) -> list[tuple[str, str, str, str, str, str, str]]:
    seen: set[tuple[str, str, str, str, str, str, str]] = set()
    duplicate_rows: list[tuple[str, str, str, str, str, str, str]] = []
    for key in row_keys_preserving_order(rows):
        if key in seen:
            duplicate_rows.append(key)
        seen.add(key)
    return duplicate_rows


def taxonomy_errors(rows: Iterable[dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for row_number, row in enumerate(rows, start=2):
        missing_fields = [field for field in REQUIRED_MATRIX_FIELDS if field not in row or row[field] is None]
        if missing_fields:
            errors.append(f"row {row_number} is missing matrix fields: {missing_fields}")
            continue
        surface = row["surface"]
        status = row["status"]
        category = row["category"]
        if surface not in SOURCE_FILES:
            errors.append(f"row {row_number} has invalid surface: {surface!r}")
        if status not in VALID_STATUSES:
            errors.append(f"row {row_number} has invalid status: {status!r}")
        if category not in VALID_CATEGORIES.get(surface, set()):
            errors.append(f"row {row_number} has invalid category for {surface!r}: {category!r}")
    return errors


def row_keys_preserving_order(
    rows: Iterable[dict[str, str]],
) -> list[tuple[str, str, str, str, str, str, str]]:
    return [
        (
            row["surface"],
            row["status"],
            row["category"],
            row["identifier"],
            row["detail"],
            row["source"],
            row["line"],
        )
        for row in rows
    ]


def surface_counts(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        surface = row["surface"]
        counts[surface] = counts.get(surface, 0) + 1
    return dict(sorted(counts.items()))


def status_counts(rows: Iterable[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        status = row["status"]
        counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def main() -> int:
    args = parse_args()
    result = validate_matrix(args.matrix, args.generated_dir, args.runtime_source)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(error)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
