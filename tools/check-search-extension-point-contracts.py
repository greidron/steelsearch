#!/usr/bin/env python3
"""Check source-derived generic search hooks are mapped to Steelsearch contracts."""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_SEARCH_REGISTRATIONS = (
    ROOT / "docs/rust-port/generated/source-search-registrations.tsv"
)
DEFAULT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"

GENERIC_HOOKS = {
    ("aggregation", "agg, builder"): (
        "aggregation",
        "registerFromPlugin(SearchPlugin::getAggregations)",
    ),
    ("aggregation", "AggregationSpec spec, ValuesSourceRegistry.Builder builder"): (
        "aggregation",
        "registerAggregation(AggregationSpec, ValuesSourceRegistry.Builder)",
    ),
    ("pipeline_aggregation", "PipelineAggregationSpec spec"): (
        "pipeline_aggregation",
        "registerPipelineAggregation(PipelineAggregationSpec)",
    ),
    ("suggester", "SuggesterSpec<?> suggester"): (
        "suggester",
        "registerSuggester(SuggesterSpec)",
    ),
    ("score_function", "ScoreFunctionSpec<?> scoreFunction"): (
        "score_function",
        "registerScoreFunction(ScoreFunctionSpec)",
    ),
    ("fetch_subphase", "FetchSubPhase subPhase"): (
        "fetch_subphase",
        "registerFetchSubPhase(FetchSubPhase)",
    ),
    ("query", "QuerySpec<?> spec"): (
        "query",
        "registerQuery(QuerySpec)",
    ),
}
ALLOWED_EXTRA_CONTRACTS = {
    (
        "aggregation_extension",
        "registerFromPlugin(SearchPlugin::getAggregationExtentions)",
    )
}
REQUIRED_EVIDENCE_TOKEN = "registry-visible"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-search-registrations",
        type=Path,
        default=DEFAULT_SOURCE_SEARCH_REGISTRATIONS,
    )
    parser.add_argument("--runtime-source", type=Path, default=DEFAULT_RUNTIME_SOURCE)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def load_source_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def runtime_contract_entries(path: Path) -> list[tuple[tuple[str, str], dict[str, str]]]:
    text = path.read_text(encoding="utf-8")
    return [
        (
            (match.group(1), match.group(2)),
            {
                "status": match.group(3),
                "evidence": match.group(4),
            },
        )
        for match in re.finditer(
            r"SearchExtensionPointContract\s*\{\s*"
            r'steelsearch_point:\s*"([^"]+)",\s*'
            r'opensearch_hook:\s*"([^"]+)",\s*'
            r'status:\s*"([^"]+)",\s*'
            r'evidence:\s*"([^"]*)",?\s*\}',
            text,
            re.MULTILINE | re.DOTALL,
        )
    ]


def runtime_contracts(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    return dict(runtime_contract_entries(path))


def check_contracts(
    source_search_registrations: Path, runtime_source: Path
) -> dict[str, object]:
    rows = load_source_rows(source_search_registrations)
    contracts = runtime_contracts(runtime_source)
    evidence_matches = evidence_external_match_summary(
        contracts,
        runtime_source=runtime_source,
        repo_root=ROOT,
    )
    duplicate_runtime_contracts = sorted(
        contract
        for contract, count in Counter(
            contract for contract, _entry in runtime_contract_entries(runtime_source)
        ).items()
        if count > 1
    )
    partial_generic_rows = [
        row
        for row in rows
        if row["status"] == "partial"
        and (row["category"], row["expression"]) in GENERIC_HOOKS
    ]
    source_category_counts = dict(
        sorted(Counter(row["category"] for row in partial_generic_rows).items())
    )
    unexpected_partial_rows = [
        {
            "category": row["category"],
            "expression": row["expression"],
            "source": row["source"],
            "line": row["line"],
        }
        for row in rows
        if row["status"] == "partial"
        and (row["category"], row["expression"]) not in GENERIC_HOOKS
    ]

    observed_generic_keys = {
        (row["category"], row["expression"]) for row in partial_generic_rows
    }
    missing_source_rows = sorted(set(GENERIC_HOOKS) - observed_generic_keys)
    missing_contracts = sorted(
        [
            {
                "category": category,
                "expression": expression,
                "steelsearch_point": point,
                "opensearch_hook": hook,
            }
            for (category, expression), (point, hook) in GENERIC_HOOKS.items()
            if (category, expression) in observed_generic_keys
            and (point, hook) not in contracts
        ],
        key=lambda item: (item["category"], item["expression"]),
    )
    expected_contracts = {
        GENERIC_HOOKS[key] for key in observed_generic_keys
    } | ALLOWED_EXTRA_CONTRACTS
    unexpected_runtime_contracts = sorted(set(contracts) - expected_contracts)
    contracts_with_wrong_status = sorted(
        [
            {
                "steelsearch_point": point,
                "opensearch_hook": hook,
                "status": contract["status"],
            }
            for (point, hook), contract in contracts.items()
            if contract["status"] != "rust-native-boundary"
        ],
        key=lambda item: (item["steelsearch_point"], item["opensearch_hook"]),
    )
    contracts_missing_evidence = sorted(
        [
            {
                "steelsearch_point": point,
                "opensearch_hook": hook,
            }
            for (point, hook), contract in contracts.items()
            if not contract["evidence"].strip()
        ],
        key=lambda item: (item["steelsearch_point"], item["opensearch_hook"]),
    )
    contracts_missing_required_evidence_token = sorted(
        [
            {
                "steelsearch_point": point,
                "opensearch_hook": hook,
                "required_token": REQUIRED_EVIDENCE_TOKEN,
            }
            for (point, hook), contract in contracts.items()
            if REQUIRED_EVIDENCE_TOKEN not in contract["evidence"]
        ],
        key=lambda item: (item["steelsearch_point"], item["opensearch_hook"]),
    )
    contracts_missing_external_evidence = sorted(
        [
            {
                "steelsearch_point": point,
                "opensearch_hook": hook,
            }
            for (point, hook), contract in contracts.items()
            if not evidence_has_external_clause(contract["evidence"], evidence_matches["corpus"])
        ],
        key=lambda item: (item["steelsearch_point"], item["opensearch_hook"]),
    )
    runtime_point_counts = dict(
        sorted(Counter(point for point, _hook in contracts).items())
    )
    errors = []
    if missing_source_rows:
        errors.append(f"missing generic source rows: {missing_source_rows[:10]}")
    if unexpected_partial_rows:
        errors.append(
            f"unexpected search registration partial rows: {unexpected_partial_rows[:10]}"
        )
    if missing_contracts:
        errors.append(f"missing runtime contracts: {missing_contracts[:10]}")
    if unexpected_runtime_contracts:
        errors.append(
            f"unexpected runtime contracts: {unexpected_runtime_contracts[:10]}"
        )
    if duplicate_runtime_contracts:
        errors.append(
            f"duplicate runtime contracts: {duplicate_runtime_contracts[:10]}"
        )
    if contracts_with_wrong_status:
        errors.append(
            f"runtime contracts have wrong status: {contracts_with_wrong_status[:10]}"
        )
    if contracts_missing_evidence:
        errors.append(
            f"runtime contracts missing evidence: {contracts_missing_evidence[:10]}"
        )
    if contracts_missing_required_evidence_token:
        errors.append(
            "runtime contracts missing registry-visible evidence: "
            f"{contracts_missing_required_evidence_token[:10]}"
        )
    if contracts_missing_external_evidence:
        errors.append(
            "runtime contracts missing externally matched evidence: "
            f"{contracts_missing_external_evidence[:10]}"
        )

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "generic_hook_count": len(GENERIC_HOOKS),
            "partial_generic_row_count": len(partial_generic_rows),
            "source_category_counts": source_category_counts,
            "runtime_contract_count": len(contracts),
            "runtime_point_counts": runtime_point_counts,
            "allowed_extra_contract_count": len(ALLOWED_EXTRA_CONTRACTS),
            "missing_source_row_count": len(missing_source_rows),
            "unexpected_partial_row_count": len(unexpected_partial_rows),
            "missing_contract_count": len(missing_contracts),
            "unexpected_runtime_contract_count": len(unexpected_runtime_contracts),
            "duplicate_runtime_contract_count": len(duplicate_runtime_contracts),
            "wrong_status_contract_count": len(contracts_with_wrong_status),
            "missing_evidence_contract_count": len(contracts_missing_evidence),
            "missing_required_evidence_token_count": len(
                contracts_missing_required_evidence_token
            ),
            "evidence_clause_count": evidence_matches["evidence_clause_count"],
            "externally_matched_evidence_clause_count": evidence_matches[
                "externally_matched_evidence_clause_count"
            ],
            "self_referential_evidence_clause_count": evidence_matches[
                "self_referential_evidence_clause_count"
            ],
            "externally_matched_contract_count": evidence_matches[
                "externally_matched_contract_count"
            ],
            "missing_external_evidence_contract_count": len(
                contracts_missing_external_evidence
            ),
        },
    }


def evidence_clauses(evidence: str) -> list[str]:
    return [clause.strip() for clause in evidence.split(";") if clause.strip()]


def evidence_has_external_clause(evidence: str, corpus: str) -> bool:
    return any(
        clause != REQUIRED_EVIDENCE_TOKEN and clause in corpus
        for clause in evidence_clauses(evidence)
    )


def evidence_external_match_summary(
    contracts: dict[tuple[str, str], dict[str, str]],
    *,
    runtime_source: Path,
    repo_root: Path,
) -> dict[str, object]:
    corpus = external_evidence_corpus(repo_root, runtime_source)
    evidence_clause_count = 0
    externally_matched_evidence_clause_count = 0
    externally_matched_contracts: set[tuple[str, str]] = set()

    for key, contract in contracts.items():
        for clause in evidence_clauses(contract["evidence"]):
            evidence_clause_count += 1
            if clause in corpus:
                externally_matched_evidence_clause_count += 1
                externally_matched_contracts.add(key)

    return {
        "corpus": corpus,
        "evidence_clause_count": evidence_clause_count,
        "externally_matched_evidence_clause_count": externally_matched_evidence_clause_count,
        "self_referential_evidence_clause_count": evidence_clause_count
        - externally_matched_evidence_clause_count,
        "externally_matched_contract_count": len(externally_matched_contracts),
    }


def external_evidence_corpus(repo_root: Path, runtime_source: Path) -> str:
    excluded = {runtime_source.resolve()}
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
    result = check_contracts(args.source_search_registrations, args.runtime_source)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
