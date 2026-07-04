#!/usr/bin/env python3
"""Check source-derived Node runtime partials have Steelsearch boundary owners."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_NODE_RUNTIME = ROOT / "docs/rust-port/generated/source-node-runtime-components.tsv"
DEFAULT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-node-runtime",
        type=Path,
        default=DEFAULT_SOURCE_NODE_RUNTIME,
    )
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def load_source_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def runtime_boundaries(path: Path) -> dict[str, dict[str, object]]:
    text = path.read_text(encoding="utf-8")
    return {
        match.group(1): {
            "steelsearch_owner": match.group(2),
            "status": match.group(3),
            "evidence": re.findall(r'"([^"]+)"', match.group(4)),
        }
        for match in re.finditer(
            r"RuntimeComponentBoundary\s*\{[^}]*"
            r'opensearch_component:\s*"([^"]+)",\s*'
            r'steelsearch_owner:\s*"([^"]+)",\s*'
            r'status:\s*"([^"]+)",\s*'
            r"evidence:\s*&\[(.*?)\],?\s*\}",
            text,
            re.MULTILINE | re.DOTALL,
        )
    }


def runtime_boundary_components(path: Path) -> set[str]:
    return set(runtime_boundaries(path))


def runtime_boundary_owners(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    return {
        match.group(1): match.group(2)
        for match in re.finditer(
            r"NodeRuntimeBoundaryOwner\s*\{\s*"
            r'opensearch_component:\s*"([^"]+)",\s*'
            r'steelsearch_owner:\s*"([^"]+)",\s*\}',
            text,
            re.MULTILINE,
        )
    }


def check_contracts(source_node_runtime: Path, runtime_source: Path) -> dict[str, object]:
    rows = load_source_rows(source_node_runtime)
    partial_components = {row["component"] for row in rows if row["status"] == "partial"}
    non_partial_rows = [
        {
            "component": row["component"],
            "status": row["status"],
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
        if row["status"] != "partial"
    ]
    owners = runtime_boundary_owners(runtime_source)
    owner_components = set(owners)
    missing_owner_components = sorted(partial_components - owner_components)
    stale_owner_components = sorted(owner_components - partial_components)
    boundaries = runtime_boundaries(runtime_source)
    code_visible_components = set(boundaries)
    code_visible_missing_from_source = sorted(code_visible_components - partial_components)
    code_visible_missing_owner = sorted(code_visible_components - owner_components)
    owner_missing_code_visible = sorted(owner_components - code_visible_components)
    boundary_owner_mismatches = sorted(
        {
            component: {
                "owner_mapping": owners[component],
                "runtime_boundary": boundaries[component]["steelsearch_owner"],
            }
            for component in owner_components & code_visible_components
            if owners[component] != boundaries[component]["steelsearch_owner"]
        }.items()
    )
    boundary_non_partial_statuses = sorted(
        {
            component: boundary["status"]
            for component, boundary in boundaries.items()
            if boundary["status"] != "partial"
        }.items()
    )
    boundary_missing_evidence = sorted(
        component
        for component, boundary in boundaries.items()
        if not boundary["evidence"]
    )

    errors = []
    if non_partial_rows:
        errors.append(f"node runtime rows are not partial: {non_partial_rows[:10]}")
    if missing_owner_components:
        errors.append(f"partial node runtime components missing owners: {missing_owner_components[:10]}")
    if stale_owner_components:
        errors.append(f"stale node runtime owner mappings: {stale_owner_components[:10]}")
    if code_visible_missing_from_source:
        errors.append(
            f"runtime boundary components missing from source inventory: {code_visible_missing_from_source[:10]}"
        )
    if code_visible_missing_owner:
        errors.append(
            f"runtime boundary components missing owner mappings: {code_visible_missing_owner[:10]}"
        )
    if owner_missing_code_visible:
        errors.append(
            f"node runtime owner mappings missing code-visible runtime boundaries: {owner_missing_code_visible[:10]}"
        )
    if boundary_owner_mismatches:
        errors.append(
            f"runtime boundary owners do not match owner mappings: {boundary_owner_mismatches[:10]}"
        )
    if boundary_non_partial_statuses:
        errors.append(
            f"runtime boundary statuses are not partial: {boundary_non_partial_statuses[:10]}"
        )
    if boundary_missing_evidence:
        errors.append(
            f"runtime boundaries missing evidence: {boundary_missing_evidence[:10]}"
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "source_node_runtime_count": len(rows),
            "partial_component_count": len(partial_components),
            "owner_mapping_count": len(owner_components),
            "code_visible_boundary_count": len(code_visible_components),
            "non_partial_row_count": len(non_partial_rows),
            "missing_owner_count": len(missing_owner_components),
            "stale_owner_count": len(stale_owner_components),
            "code_visible_missing_from_source_count": len(code_visible_missing_from_source),
            "code_visible_missing_owner_count": len(code_visible_missing_owner),
            "owner_missing_code_visible_count": len(owner_missing_code_visible),
            "boundary_owner_mismatch_count": len(boundary_owner_mismatches),
            "boundary_non_partial_status_count": len(boundary_non_partial_statuses),
            "boundary_missing_evidence_count": len(boundary_missing_evidence),
        },
    }


def main() -> int:
    args = parse_args()
    result = check_contracts(args.source_node_runtime, args.runtime_source)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
