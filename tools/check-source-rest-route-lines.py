#!/usr/bin/env python3
"""Validate source REST route rows still match source windows."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


DEFAULT_SOURCE = Path("docs/rust-port/generated/source-rest-routes.tsv")
WINDOW_LINES = 12


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", nargs="?", default=str(DEFAULT_SOURCE))
    parser.add_argument("--format", choices=("json", "text"), default="text")
    return parser.parse_args()


def validate_source(source: Path) -> dict[str, object]:
    errors: list[str] = []
    checked = 0
    with source.open(newline="", encoding="utf-8") as source_file:
        for row_number, row in enumerate(csv.DictReader(source_file, delimiter="\t"), start=2):
            checked += 1
            errors.extend(validate_row(row, row_number))
    return {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "passed": not errors,
            "checked_rows": checked,
            "window_lines": WINDOW_LINES,
        },
    }


def validate_row(row: dict[str, str], row_number: int) -> list[str]:
    errors: list[str] = []
    source_path = Path(row.get("source") or "")
    method = row.get("method") or ""
    path_expression = row.get("path_or_expression") or ""
    line_text = row.get("line") or ""
    if not source_path.is_file():
        return [f"row {row_number}: source file is missing: {source_path}"]
    try:
        line_number = int(line_text)
    except ValueError:
        return [f"row {row_number}: line is not an integer: {line_text!r}"]
    lines = source_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    if line_number < 1 or line_number > len(lines):
        return [
            f"row {row_number}: line {line_number} is outside {source_path} length {len(lines)}"
        ]
    window = "\n".join(lines[line_number - 1 : line_number - 1 + WINDOW_LINES])
    if method and method not in window:
        errors.append(
            f"row {row_number}: method {method} not found near {source_path}:{line_number}"
        )
    if normalize(path_expression) not in normalize(window):
        errors.append(
            f"row {row_number}: path expression {path_expression} not found near {source_path}:{line_number}"
        )
    return errors


def normalize(value: str) -> str:
    return " ".join(value.replace('"', "").split())


def main() -> int:
    args = parse_args()
    result = validate_source(Path(args.source))
    if args.format == "json":
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(f"{result['status']}: {result['summary']}")
        for error in result["errors"]:
            print(error)
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
