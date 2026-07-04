#!/usr/bin/env python3
"""Check source-derived Node runtime partials have Steelsearch boundary owners."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_NODE_RUNTIME = ROOT / "docs/rust-port/generated/source-node-runtime-components.tsv"
DEFAULT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"
EXPECTED_NODE_RUNTIME_KINDS = {"controller", "module", "registry", "service"}

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


def runtime_boundary_entries(path: Path) -> list[tuple[str, dict[str, object]]]:
    text = path.read_text(encoding="utf-8")
    return [
        (
            match.group(1),
            {
                "steelsearch_owner": match.group(2),
                "status": match.group(3),
                "evidence": re.findall(r'"([^"]+)"', match.group(4)),
            },
        )
        for match in re.finditer(
            r"RuntimeComponentBoundary\s*\{[^}]*"
            r'opensearch_component:\s*"([^"]+)",\s*'
            r'steelsearch_owner:\s*"([^"]+)",\s*'
            r'status:\s*"([^"]+)",\s*'
            r"evidence:\s*&\[(.*?)\],?\s*\}",
            text,
            re.MULTILINE | re.DOTALL,
        )
    ]


def runtime_boundaries(path: Path) -> dict[str, dict[str, object]]:
    return dict(runtime_boundary_entries(path))


def runtime_boundary_components(path: Path) -> set[str]:
    return set(runtime_boundaries(path))


def runtime_boundary_owners(path: Path) -> dict[str, str]:
    return dict(runtime_boundary_owner_entries(path))


def runtime_boundary_owner_entries(path: Path) -> list[tuple[str, str]]:
    text = path.read_text(encoding="utf-8")
    return [
        (match.group(1), match.group(2))
        for match in re.finditer(
            r"NodeRuntimeBoundaryOwner\s*\{\s*"
            r'opensearch_component:\s*"([^"]+)",\s*'
            r'steelsearch_owner:\s*"([^"]+)",\s*\}',
            text,
            re.MULTILINE,
        )
    ]


def check_contracts(source_node_runtime: Path, runtime_source: Path) -> dict[str, object]:
    rows = load_source_rows(source_node_runtime)
    source_anchor_surface_required = is_current_default_pair(
        source_node_runtime, runtime_source
    )
    missing_source_anchor_surface = (
        node_runtime_source_anchor_surface_missing(runtime_source)
        if source_anchor_surface_required
        else []
    )
    source_components = {row["component"] for row in rows}
    component_kinds = {
        row["component"]: row["kind"]
        for row in rows
    }
    component_statuses = {row["component"]: row["status"] for row in rows}
    unexpected_kinds = sorted(
        {
            row["kind"]
            for row in rows
            if row["kind"] not in EXPECTED_NODE_RUNTIME_KINDS
        }
    )
    source_kind_counts = kind_counts(source_components, component_kinds)
    unsupported_status_rows = [
        {
            "component": row["component"],
            "status": row["status"],
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
        if row["status"] not in {"partial", "implemented"}
    ]
    owners = runtime_boundary_owners(runtime_source)
    owner_duplicate_components = sorted(
        component
        for component, count in Counter(
            component for component, _owner in runtime_boundary_owner_entries(runtime_source)
        ).items()
        if count > 1
    )
    owner_components = set(owners)
    owner_kind_counts = kind_counts(owner_components & source_components, component_kinds)
    missing_owner_components = sorted(source_components - owner_components)
    stale_owner_components = sorted(owner_components - source_components)
    boundaries = runtime_boundaries(runtime_source)
    boundary_duplicate_components = sorted(
        component
        for component, count in Counter(
            component for component, _boundary in runtime_boundary_entries(runtime_source)
        ).items()
        if count > 1
    )
    code_visible_components = set(boundaries)
    code_visible_kind_counts = kind_counts(code_visible_components & source_components, component_kinds)
    code_visible_missing_from_source = sorted(code_visible_components - source_components)
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
    boundary_status_mismatches = sorted(
        {
            component: {
                "source": component_statuses.get(component),
                "runtime_boundary": boundary["status"],
            }
            for component, boundary in boundaries.items()
            if component in component_statuses
            and boundary["status"] != component_statuses[component]
        }.items()
    )
    boundary_missing_evidence = sorted(
        component
        for component, boundary in boundaries.items()
        if not boundary["evidence"]
    )
    evidence_matches = evidence_external_match_summary(
        boundaries,
        runtime_source=runtime_source,
        repo_root=ROOT,
    )

    errors = []
    if unsupported_status_rows:
        errors.append(f"node runtime rows have unsupported status: {unsupported_status_rows[:10]}")
    if unexpected_kinds:
        errors.append(f"unexpected node runtime source kinds: {unexpected_kinds[:10]}")
    if missing_owner_components:
        errors.append(f"partial node runtime components missing owners: {missing_owner_components[:10]}")
    if stale_owner_components:
        errors.append(f"stale node runtime owner mappings: {stale_owner_components[:10]}")
    if owner_duplicate_components:
        errors.append(
            f"duplicate node runtime owner mappings: {owner_duplicate_components[:10]}"
        )
    if boundary_duplicate_components:
        errors.append(
            f"duplicate runtime boundary components: {boundary_duplicate_components[:10]}"
        )
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
    if boundary_status_mismatches:
        errors.append(
            f"runtime boundary statuses do not match source rows: {boundary_status_mismatches[:10]}"
        )
    if boundary_missing_evidence:
        errors.append(
            f"runtime boundaries missing evidence: {boundary_missing_evidence[:10]}"
        )
    if missing_source_anchor_surface:
        errors.append(
            "runtime source is missing node runtime source-anchor surface: "
            f"{missing_source_anchor_surface}"
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "source_node_runtime_count": len(rows),
            "covered_component_count": len(source_components),
            "source_kind_counts": source_kind_counts,
            "owner_mapping_count": len(owner_components),
            "owner_kind_counts": owner_kind_counts,
            "code_visible_boundary_count": len(code_visible_components),
            "code_visible_kind_counts": code_visible_kind_counts,
            "duplicate_owner_mapping_count": len(owner_duplicate_components),
            "duplicate_boundary_component_count": len(boundary_duplicate_components),
            "unsupported_status_row_count": len(unsupported_status_rows),
            "unexpected_kind_count": len(unexpected_kinds),
            "missing_owner_count": len(missing_owner_components),
            "stale_owner_count": len(stale_owner_components),
            "code_visible_missing_from_source_count": len(code_visible_missing_from_source),
            "code_visible_missing_owner_count": len(code_visible_missing_owner),
            "owner_missing_code_visible_count": len(owner_missing_code_visible),
            "boundary_owner_mismatch_count": len(boundary_owner_mismatches),
            "boundary_status_mismatch_count": len(boundary_status_mismatches),
            "boundary_missing_evidence_count": len(boundary_missing_evidence),
            "evidence_item_count": evidence_matches["evidence_item_count"],
            "externally_matched_evidence_count": evidence_matches[
                "externally_matched_evidence_count"
            ],
            "self_referential_evidence_count": evidence_matches[
                "self_referential_evidence_count"
            ],
            "externally_matched_boundary_count": evidence_matches[
                "externally_matched_boundary_count"
            ],
            "self_referential_boundary_count": evidence_matches[
                "self_referential_boundary_count"
            ],
            "source_anchor_surface_required": source_anchor_surface_required,
            "missing_source_anchor_surface_count": len(missing_source_anchor_surface),
        },
    }


def is_current_default_pair(source_node_runtime: Path, runtime_source: Path) -> bool:
    try:
        return (
            source_node_runtime.resolve() == DEFAULT_SOURCE_NODE_RUNTIME.resolve()
            and runtime_source.resolve() == DEFAULT_RUNTIME_SOURCE.resolve()
        )
    except OSError:
        return False


def node_runtime_source_anchor_surface_missing(runtime_source: Path) -> list[str]:
    text = runtime_source.read_text(encoding="utf-8")
    required_tokens = {
        "generated TSV include": (
            'include_str!("../../../docs/rust-port/generated/source-node-runtime-components.tsv")'
        ),
        "source anchor struct": "pub struct NodeRuntimeSourceAnchor",
        "source anchor status field": "pub status: String",
        "source anchor kind field": "pub kind: String",
        "source anchor component field": "pub component: String",
        "source anchor source field": "pub source: String",
        "source anchor line field": "pub line: u32",
        "source anchor function": "pub fn node_runtime_source_anchors()",
        "dev endpoint key": '"node_runtime_source_anchors": node_runtime_source_anchors()',
    }
    return [
        label
        for label, token in required_tokens.items()
        if token not in text
    ]


def kind_counts(components: set[str], component_kinds: dict[str, str]) -> dict[str, int]:
    counts = {kind: 0 for kind in sorted(EXPECTED_NODE_RUNTIME_KINDS)}
    for component in components:
        kind = component_kinds.get(component)
        if kind in counts:
            counts[kind] += 1
    return counts


def evidence_external_match_summary(
    boundaries: dict[str, dict[str, object]],
    *,
    runtime_source: Path,
    repo_root: Path,
) -> dict[str, int]:
    searchable_text = external_evidence_corpus(repo_root, runtime_source)
    evidence_item_count = 0
    externally_matched_evidence_count = 0
    externally_matched_components: set[str] = set()

    for component, boundary in boundaries.items():
        for evidence in boundary["evidence"]:
            evidence_item_count += 1
            if evidence and evidence in searchable_text:
                externally_matched_evidence_count += 1
                externally_matched_components.add(component)

    return {
        "evidence_item_count": evidence_item_count,
        "externally_matched_evidence_count": externally_matched_evidence_count,
        "self_referential_evidence_count": evidence_item_count
        - externally_matched_evidence_count,
        "externally_matched_boundary_count": len(externally_matched_components),
        "self_referential_boundary_count": len(boundaries)
        - len(externally_matched_components),
    }


def external_evidence_corpus(repo_root: Path, runtime_source: Path) -> str:
    excluded = {
        runtime_source.resolve(),
        runtime_source.with_name(f"{runtime_source.name}.pre-actix-backup").resolve(),
    }
    chunks: list[str] = []
    for directory_name in ("docs", "tools", "crates"):
        directory = repo_root / directory_name
        if not directory.exists():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            try:
                resolved = path.resolve()
            except OSError:
                continue
            if resolved in excluded:
                continue
            try:
                chunks.append(path.read_text(encoding="utf-8"))
            except UnicodeDecodeError:
                continue
            except OSError:
                continue
    return "\n".join(chunks)


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
