#!/usr/bin/env python3
"""Validate promotion-readiness ledger coverage for source-derived partial rows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "docs/rust-port/generated/source-compatibility-matrix.tsv"
DEFAULT_LEDGER = ROOT / "tools/fixtures/source-partial-promotion-readiness.json"
ALLOWED_BUCKETS = {"promotion-blocked", "promotion-ready"}
ALLOWED_LEDGER_STATUSES = {"partial", "implemented"}
ALLOWED_EVIDENCE_CLASSES = {
    "boundary mapping",
    "route parity",
    "semantic parity",
    "durability parity",
    "distributed parity",
}
REQUIRED_FIELDS = {
    "surface",
    "status",
    "category",
    "expected_count",
    "promotion_bucket",
    "current_contract_gate",
    "current_evidence_artifacts",
    "current_evidence_classes",
    "missing_required_classes",
    "required_for_implemented",
    "blocker",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def group_counts(matrix_path: Path) -> dict[tuple[str, str, str], int]:
    counts: dict[tuple[str, str, str], int] = {}
    for row in read_rows(matrix_path):
        key = (row["surface"], row["status"], row["category"])
        counts[key] = counts.get(key, 0) + 1
    return counts


def open_partial_group_counts(matrix_path: Path) -> dict[tuple[str, str, str], int]:
    return {
        key: count
        for key, count in group_counts(matrix_path).items()
        if key[1] == "partial"
    }


def load_ledger(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    entries = payload.get("entries")
    if not isinstance(entries, list):
        raise ValueError("ledger must contain an entries array")
    return entries


def check_readiness(matrix_path: Path, ledger_path: Path) -> dict[str, Any]:
    matrix_counts = group_counts(matrix_path)
    partial_matrix_counts = {
        key: count for key, count in matrix_counts.items() if key[1] == "partial"
    }
    entries = load_ledger(ledger_path)
    errors: list[str] = []
    entry_counts: dict[tuple[str, str, str], int] = {}
    bucket_counts: dict[str, int] = {}
    current_evidence_class_counts: dict[str, int] = {}
    missing_required_class_counts: dict[str, int] = {}

    for index, entry in enumerate(entries):
        missing = sorted(REQUIRED_FIELDS - set(entry))
        if missing:
            errors.append(f"entry {index} missing required fields: {missing}")
            continue
        key = (entry["surface"], entry["status"], entry["category"])
        entry_counts[key] = entry_counts.get(key, 0) + 1
        bucket = entry["promotion_bucket"]
        bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        if bucket not in ALLOWED_BUCKETS:
            errors.append(f"{key}: unsupported promotion_bucket {bucket!r}")
        if entry["status"] not in ALLOWED_LEDGER_STATUSES:
            errors.append(f"{key}: unsupported ledger status {entry['status']!r}")
        if not isinstance(entry["expected_count"], int) or entry["expected_count"] <= 0:
            errors.append(f"{key}: expected_count must be a positive integer")
        matrix_count = matrix_counts.get(key, 0)
        if matrix_count == 0:
            errors.append(f"{key}: no matching matrix rows for readiness entry")
        elif entry["status"] == "partial" and entry["expected_count"] != matrix_count:
            errors.append(
                f"{key}: expected_count {entry['expected_count']} does not match matrix count {matrix_count}"
            )
        elif entry["status"] == "implemented" and entry["expected_count"] > matrix_count:
            errors.append(
                f"{key}: expected_count {entry['expected_count']} exceeds matrix count {matrix_count}"
            )
        if not entry["current_contract_gate"]:
            errors.append(f"{key}: current_contract_gate is required")
        elif not resolve_repo_path(entry["current_contract_gate"], ledger_path).exists():
            errors.append(
                f"{key}: current_contract_gate does not exist: {entry['current_contract_gate']}"
            )
        evidence_artifacts = entry["current_evidence_artifacts"]
        if not isinstance(evidence_artifacts, list) or not evidence_artifacts:
            errors.append(f"{key}: current_evidence_artifacts must be a non-empty list")
        else:
            for artifact in evidence_artifacts:
                if not isinstance(artifact, str) or not artifact:
                    errors.append(f"{key}: current_evidence_artifacts contains an invalid path")
                    continue
                if not resolve_repo_path(artifact, ledger_path).exists():
                    errors.append(f"{key}: evidence artifact does not exist: {artifact}")
        required = entry["required_for_implemented"]
        if not isinstance(required, list) or not required:
            errors.append(f"{key}: required_for_implemented must be a non-empty list")
            required_classes: set[str] = set()
        else:
            required_classes = set(required)
            unsupported_required = sorted(required_classes - ALLOWED_EVIDENCE_CLASSES)
            if unsupported_required:
                errors.append(f"{key}: unsupported required_for_implemented classes {unsupported_required}")
        current_evidence_classes = entry["current_evidence_classes"]
        if not isinstance(current_evidence_classes, list) or not current_evidence_classes:
            errors.append(f"{key}: current_evidence_classes must be a non-empty list")
            current_classes: set[str] = set()
        else:
            current_classes = set(current_evidence_classes)
            unsupported_current = sorted(current_classes - ALLOWED_EVIDENCE_CLASSES)
            if unsupported_current:
                errors.append(f"{key}: unsupported current_evidence_classes {unsupported_current}")
            for evidence_class in current_classes:
                current_evidence_class_counts[evidence_class] = (
                    current_evidence_class_counts.get(evidence_class, 0) + 1
                )
        computed_missing_classes = sorted(required_classes - current_classes)
        declared_missing_classes = entry["missing_required_classes"]
        if not isinstance(declared_missing_classes, list):
            errors.append(f"{key}: missing_required_classes must be a list")
        else:
            unsupported_missing = sorted(set(declared_missing_classes) - ALLOWED_EVIDENCE_CLASSES)
            if unsupported_missing:
                errors.append(f"{key}: unsupported missing_required_classes {unsupported_missing}")
            if sorted(declared_missing_classes) != computed_missing_classes:
                errors.append(
                    f"{key}: missing_required_classes {sorted(declared_missing_classes)} "
                    f"does not match computed missing classes {computed_missing_classes}"
                )
            if bucket == "promotion-blocked" and not declared_missing_classes:
                errors.append(f"{key}: promotion-blocked entries must declare missing required classes")
            if bucket == "promotion-ready" and declared_missing_classes:
                errors.append(f"{key}: promotion-ready entries must not declare missing required classes")
        for missing_class in computed_missing_classes:
            missing_required_class_counts[missing_class] = (
                missing_required_class_counts.get(missing_class, 0) + 1
            )
        if not entry["blocker"]:
            errors.append(f"{key}: blocker is required")

    duplicate_keys = sorted(key for key, count in entry_counts.items() if count > 1)
    missing_keys = sorted(set(partial_matrix_counts) - set(entry_counts))
    extra_keys = sorted(set(entry_counts) - set(matrix_counts))
    if duplicate_keys:
        errors.append(f"duplicate ledger groups: {duplicate_keys[:10]}")
    if missing_keys:
        errors.append(f"partial matrix groups missing readiness entries: {missing_keys[:10]}")
    if extra_keys:
        errors.append(f"readiness entries without partial matrix groups: {extra_keys[:10]}")

    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "matrix_partial_group_count": len(partial_matrix_counts),
            "matrix_covered_group_count": sum(
                1 for key in entry_counts if key in matrix_counts
            ),
            "ledger_entry_count": len(entries),
            "missing_group_count": len(missing_keys),
            "extra_group_count": len(extra_keys),
            "duplicate_group_count": len(duplicate_keys),
            "bucket_counts": dict(sorted(bucket_counts.items())),
            "current_evidence_class_counts": dict(
                sorted(current_evidence_class_counts.items())
            ),
            "missing_required_class_counts": dict(
                sorted(missing_required_class_counts.items())
            ),
            "evidence_artifact_count": sum(
                len(entry.get("current_evidence_artifacts", []))
                for entry in entries
                if isinstance(entry.get("current_evidence_artifacts"), list)
            ),
            "matrix_partial_row_count": sum(partial_matrix_counts.values()),
            "ledger_expected_row_count": sum(
                entry.get("expected_count", 0)
                for entry in entries
                if isinstance(entry.get("expected_count"), int)
            ),
        },
    }


def resolve_repo_path(value: str, ledger_path: Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    ledger_relative = ledger_path.parent / path
    if ledger_relative.exists():
        return ledger_relative
    return ROOT / path


def main() -> int:
    args = parse_args()
    result = check_readiness(args.matrix, args.ledger)
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
