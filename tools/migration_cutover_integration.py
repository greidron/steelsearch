#!/usr/bin/env python3
"""Run a bounded OpenSearch-export to Steelsearch-import cutover integration check."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "migration-cutover-integration.json"
DEFAULT_OUTPUT = ROOT / "target" / "migration-cutover-integration-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--output",
        default=os.environ.get("MIGRATION_CUTOVER_INTEGRATION_REPORT", str(DEFAULT_OUTPUT)),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args()


def request_json(
    base_url: str,
    method: str,
    path: str,
    body: Any | None,
    timeout: float,
) -> dict[str, Any]:
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
    request = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=payload,
        method=method,
    )
    if payload is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return decode_response(response.status, response.read())
    except urllib.error.HTTPError as error:
        return decode_response(error.code, error.read())


def decode_response(status: int, payload: bytes) -> dict[str, Any]:
    text = payload.decode("utf-8", errors="replace") if payload else ""
    body = None
    if text:
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = None
    return {
        "status": status,
        "body": body,
        "body_text": text,
    }


def extract_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index >= len(current):
                return None
            current = current[index]
            continue
        if not isinstance(current, dict):
            return None
        if token not in current:
            return None
        current = current[token]
    return current


def search_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
    }


def path_summary(response: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    body = response.get("body") or {}
    summary: dict[str, Any] = {"status": response.get("status")}
    for path in paths:
        summary[path] = extract_path(body, path)
    return summary


def summarize_response(check: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    extractor = check.get("extract")
    if extractor == "search_summary":
        return search_summary(response)
    if extractor == "path_summary":
        return path_summary(response, check.get("compare_paths", []))
    if check.get("compare_paths"):
        return path_summary(response, check["compare_paths"])
    return {
        "status": response.get("status"),
        "body": response.get("body"),
        "body_text": response.get("body_text"),
    }


def run_operation(
    base_url: str,
    operation: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    response = request_json(
        base_url,
        operation["method"],
        operation["path"],
        operation.get("body"),
        timeout,
    )
    return {
        "name": operation["name"],
        "method": operation["method"],
        "path": operation["path"],
        **response,
    }


def legacy_fixture_to_operations_and_checks(fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index = fixture["index"]
    operations: list[dict[str, Any]] = [
        {
            "name": "create_index",
            "method": "PUT",
            "path": f"/{index}",
            "body": {
                "settings": fixture["settings"],
                "mappings": fixture["mappings"],
            },
        }
    ]
    for entry in fixture["docs"]:
        operations.append(
            {
                "name": f"put_{entry['id']}",
                "method": "PUT",
                "path": f"/{index}/_doc/{entry['id']}?refresh=wait_for",
                "body": entry["source"],
            }
        )
    checks = [
        {
            "name": "index_search",
            "method": "POST",
            "path": f"/{index}/_search",
            "body": fixture["query"],
            "extract": "search_summary",
        }
    ]
    return operations, checks


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url or not args.opensearch_url:
        print("Both STEELSEARCH_URL and OPENSEARCH_URL are required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    operations = fixture.get("operations")
    checks = fixture.get("checks")
    if operations is None or checks is None:
        operations, checks = legacy_fixture_to_operations_and_checks(fixture)

    report: dict[str, Any] = {
        "name": fixture.get("name", "migration-cutover-integration"),
        "fixture": str(Path(args.fixture).resolve()),
        "source": args.opensearch_url,
        "target": args.steelsearch_url,
        "steps": [],
        "checks": [],
        "comparison": {},
    }

    for operation in operations:
        source_step = run_operation(args.opensearch_url, operation, args.timeout)
        source_step["target"] = "source"
        report["steps"].append(source_step)

    for operation in operations:
        target_step = run_operation(args.steelsearch_url, operation, args.timeout)
        target_step["target"] = "target"
        report["steps"].append(target_step)

    for check in checks:
        source_response = request_json(
            args.opensearch_url,
            check["method"],
            check["path"],
            check.get("body"),
            args.timeout,
        )
        target_response = request_json(
            args.steelsearch_url,
            check["method"],
            check["path"],
            check.get("body"),
            args.timeout,
        )
        source_summary = summarize_response(check, source_response)
        target_summary = summarize_response(check, target_response)
        report["checks"].append(
            {
                "name": check["name"],
                "source": source_summary,
                "target": target_summary,
                "match": source_summary == target_summary,
            }
        )

    overall_match = all(check["match"] for check in report["checks"])
    report["comparison"] = {
        "match": overall_match,
        "checks": report["checks"],
    }
    if report["checks"]:
        report["comparison"]["source"] = report["checks"][0]["source"]
        report["comparison"]["target"] = report["checks"][0]["target"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if overall_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
