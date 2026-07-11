#!/usr/bin/env python3
"""Run multi-node write-path integration checks with optional OpenSearch comparison."""

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
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "multi-node-write-path.json"
DEFAULT_OUTPUT = ROOT / "target" / "multi-node-write-path-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-a-url", default=os.environ.get("STEELSEARCH_NODE_A_URL"))
    parser.add_argument("--node-b-url", default=os.environ.get("STEELSEARCH_NODE_B_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--output",
        default=os.environ.get("MULTI_NODE_WRITE_PATH_REPORT", str(DEFAULT_OUTPUT)),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args()


def encode_request_body(case: dict[str, Any]) -> bytes | None:
    if "body" not in case:
        return None
    body = case["body"]
    if isinstance(body, (dict, list)):
        return json.dumps(body).encode("utf-8")
    if isinstance(body, str):
        return body.encode("utf-8")
    raise TypeError(f"unsupported request body type: {type(body)!r}")


def request_response(base_url: str, case: dict[str, Any], timeout: float) -> dict[str, Any]:
    body = encode_request_body(case)
    request = urllib.request.Request(
        base_url.rstrip("/") + case["path"],
        data=body,
        method=case["method"],
    )
    if body is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return decode_response(response.status, payload)
    except urllib.error.HTTPError as error:
        payload = error.read()
        return decode_response(error.code, payload)
    except urllib.error.URLError as error:
        return {
            "status": None,
            "body": None,
            "body_text": None,
            "error": str(error.reason),
        }


def request_path(base_url: str, method: str, path: str, timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(base_url.rstrip("/") + path, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return decode_response(response.status, response.read())
    except urllib.error.HTTPError as error:
        return decode_response(error.code, error.read())
    except urllib.error.URLError as error:
        return {
            "status": None,
            "body": None,
            "body_text": None,
            "error": str(error.reason),
        }


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
    for segment in path.split("."):
        if isinstance(current, list):
            try:
                current = current[int(segment)]
            except (ValueError, IndexError):
                return None
            continue
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def check_case(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    compare = case.get("compare", {})
    expected_status = compare.get("expected_status")
    if expected_status is not None and response.get("status") != expected_status:
        errors.append(f"expected status {expected_status} but got {response.get('status')}")

    for path in compare.get("body_paths_present", []):
        if extract_path(response.get("body"), path) is None:
            errors.append(f"missing body path [{path}]")

    for path, expected in compare.get("body_paths_exact", {}).items():
        actual = extract_path(response.get("body"), path)
        if actual != expected:
            errors.append(f"body path [{path}] expected {expected!r} but got {actual!r}")
    return errors


def fixture_indices(fixture: dict[str, Any]) -> list[str]:
    indices: list[str] = []
    seen: set[str] = set()
    for case in fixture.get("cases", []):
        if case.get("method") != "PUT":
            continue
        path = str(case.get("path") or "")
        if not path.startswith("/") or path.startswith("/_") or "/_" in path.strip("/"):
            continue
        index = path.strip("/")
        if index and index not in seen:
            seen.add(index)
            indices.append(index)
    return indices


def cleanup_indices(base_url: str, fixture: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    reports = []
    for index in fixture_indices(fixture):
        reports.append(
            {
                "name": f"delete_index:{index}",
                **request_path(base_url, "DELETE", f"/{index}", timeout),
            }
        )
    return reports


def run_cases(
    targets: dict[str, str],
    fixture: dict[str, Any],
    timeout: float,
) -> tuple[list[dict[str, Any]], dict[str, int], int]:
    cases = []
    summary = {"passed": 0, "failed": 0}
    exit_code = 0
    for case in fixture.get("cases", []):
        base_url = targets[case["target"]]
        response = request_response(base_url, case, timeout)
        errors = check_case(case, response)
        status = "passed" if not errors else "failed"
        if errors:
            exit_code = 1
            summary["failed"] += 1
        else:
            summary["passed"] += 1
        cases.append(
            {
                "name": case["name"],
                "target": case["target"],
                "status": status,
                "response": response,
                "errors": errors,
            }
        )
    return cases, summary, exit_code


def main() -> int:
    args = parse_args()
    if not args.node_a_url or not args.node_b_url:
        print(
            "Both STEELSEARCH_NODE_A_URL and STEELSEARCH_NODE_B_URL are required",
            file=sys.stderr,
        )
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    steelsearch_targets = {
        "node_a": args.node_a_url,
        "node_b": args.node_b_url,
    }
    report: dict[str, Any] = {
        "name": fixture.get("name", "multi-node-write-path"),
        "fixture": str(Path(args.fixture).resolve()),
        "targets": steelsearch_targets.copy(),
        "setup": {"steelsearch": cleanup_indices(args.node_a_url, fixture, args.timeout)},
        "cases": [],
        "summary": {
            "passed": 0,
            "failed": 0,
        },
    }

    steel_cases, steel_summary, exit_code = run_cases(steelsearch_targets, fixture, args.timeout)
    report["summary"] = steel_summary

    if args.opensearch_url:
        opensearch_targets = {
            "node_a": args.opensearch_url,
            "node_b": args.opensearch_url,
        }
        report["targets"]["opensearch"] = args.opensearch_url
        report["setup"]["opensearch"] = cleanup_indices(args.opensearch_url, fixture, args.timeout)
        open_cases, _, open_exit_code = run_cases(opensearch_targets, fixture, args.timeout)
        open_by_name = {case["name"]: case for case in open_cases}
        report["cases"] = []
        report["summary"] = {"passed": 0, "failed": 0}
        for steel_case in steel_cases:
            open_case = open_by_name.get(steel_case["name"], {})
            errors = []
            if steel_case.get("status") != "passed":
                errors.extend(f"steelsearch {error}" for error in steel_case.get("errors", []))
            if not open_case:
                errors.append("opensearch missing case result")
            if open_case.get("status") != "passed":
                errors.extend(f"opensearch {error}" for error in open_case.get("errors", []))
            status = "passed" if not errors else "failed"
            report["summary"]["passed" if status == "passed" else "failed"] += 1
            report["cases"].append(
                {
                    "name": steel_case["name"],
                    "target": steel_case["target"],
                    "status": status,
                    "steelsearch": steel_case.get("response"),
                    "opensearch": open_case.get("response"),
                    "errors": errors,
                }
            )
        exit_code = 1 if report["summary"]["failed"] or open_exit_code else exit_code
    else:
        report["cases"] = steel_cases

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
