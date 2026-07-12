#!/usr/bin/env python3
"""Report non-closed source compatibility rows and verify gap ownership."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MATRIX = ROOT / "docs/rust-port/generated/source-compatibility-matrix.tsv"
CLOSED_STATUSES = {"implemented", "out-of-scope"}
GAP_OWNERS = {
    ("node_runtime", "partial"): "docs/rust-port/node-runtime-gap-inventory.md",
    ("node_runtime", "planned"): "docs/rust-port/node-runtime-gap-inventory.md",
    ("search_registration", "partial"): "docs/rust-port/source-compatibility-matrix.md#matrix-gaps-to-close",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--format", choices=("json", "text"), default="text")
    parser.add_argument("--require-all-gaps-mapped", action="store_true")
    return parser.parse_args()


def report_gaps(matrix_path: Path) -> dict[str, Any]:
    rows = read_rows(matrix_path)
    open_rows = [row for row in rows if row["status"] not in CLOSED_STATUSES]
    unmapped = unmapped_gap_keys(open_rows)
    return {
        "status": "ok" if not unmapped else "failed",
        "errors": [f"unmapped gap owner for {surface}/{status}" for surface, status in unmapped],
        "summary": {
            "matrix_row_count": len(rows),
            "matrix_row_digest": stable_row_digest(rows),
            "closed_row_count": len(rows) - len(open_rows),
            "closed_row_digest": stable_row_digest(
                row for row in rows if row["status"] in CLOSED_STATUSES
            ),
            "open_gap_row_count": len(open_rows),
            "open_gap_counts": open_gap_counts(open_rows),
            "unmapped_gap_count": len(unmapped),
        },
        "gap_groups": gap_groups(open_rows),
    }


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as source_file:
        return list(csv.DictReader(source_file, delimiter="\t"))


def stable_row_digest(rows: Any) -> str:
    normalized = [
        {key: str(value) for key, value in sorted(row.items())}
        for row in rows
        if isinstance(row, dict)
    ]
    encoded = json.dumps(sorted(normalized, key=json.dumps), separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def unmapped_gap_keys(rows: list[dict[str, str]]) -> list[tuple[str, str]]:
    keys = sorted({(row["surface"], row["status"]) for row in rows})
    return [key for key in keys if key not in GAP_OWNERS]


def open_gap_counts(rows: list[dict[str, str]]) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for row in rows:
        surface_counts = counts.setdefault(row["surface"], {})
        status = row["status"]
        surface_counts[status] = surface_counts.get(status, 0) + 1
    return {surface: dict(sorted(statuses.items())) for surface, statuses in sorted(counts.items())}


def gap_groups(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str], list[dict[str, str]]] = {}
    for row in rows:
        key = (row["surface"], row["status"], row["category"])
        groups.setdefault(key, []).append(row)
    return [
        {
            "surface": surface,
            "status": status,
            "category": category,
            "owner": GAP_OWNERS.get((surface, status)),
            "count": len(group_rows),
            "examples": [
                {
                    "identifier": row["identifier"],
                    "detail": row["detail"],
                    "source": row["source"],
                    "line": row["line"],
                }
                for row in group_rows[:10]
            ],
        }
        for (surface, status, category), group_rows in sorted(groups.items())
    ]


def text_report(report: dict[str, Any]) -> str:
    lines = [f"{report['status']}: {report['summary']}"]
    for group in report["gap_groups"]:
        lines.append(
            f"- {group['surface']}/{group['status']}/{group['category']}: "
            f"{group['count']} owner={group['owner']}"
        )
    for error in report["errors"]:
        lines.append(error)
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    report = report_gaps(args.matrix)
    output = json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else text_report(report)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(output + "\n", encoding="utf-8")
    else:
        print(output)
    if args.require_all_gaps_mapped and report["status"] != "ok":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
