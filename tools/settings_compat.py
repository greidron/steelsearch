#!/usr/bin/env python3
"""Run settings HTTP compatibility checks against Steelsearch and OpenSearch."""

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
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "settings-compat.json"
DEFAULT_OUTPUT = ROOT / "target" / "settings-compat-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--output",
        default=os.environ.get("SETTINGS_COMPAT_REPORT", str(DEFAULT_OUTPUT)),
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
        if not isinstance(current, dict):
            return None
        current = current.get(segment)
        if current is None:
            return None
    return current


def check_target(case: dict[str, Any], response: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    compare = case.get("compare", {})
    expected_status = compare.get("expected_status")
    if expected_status is not None and response.get("status") != expected_status:
        errors.append(f"expected status {expected_status} but got {response.get('status')}")

    for path in compare.get("body_paths_present", []):
        if extract_path(response.get("body"), path) is None:
            errors.append(f"missing body path [{path}]")

    for path in compare.get("body_paths_absent", []):
        if extract_path(response.get("body"), path) is not None:
            errors.append(f"unexpected body path [{path}]")
    return errors


def compare_targets(case: dict[str, Any], steelsearch: dict[str, Any], opensearch: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    compare = case.get("compare", {})
    for path in compare.get("body_paths_equal", []):
        left = extract_path(steelsearch.get("body"), path)
        right = extract_path(opensearch.get("body"), path)
        if left != right:
            errors.append(f"body path [{path}] drift: steelsearch={left!r} opensearch={right!r}")
    return errors


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url or not args.opensearch_url:
        print("Both STEELSEARCH_URL and OPENSEARCH_URL are required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    report: dict[str, Any] = {
        "name": fixture.get("name", "settings-compat"),
        "fixture": str(Path(args.fixture).resolve()),
        "targets": {
            "steelsearch": args.steelsearch_url,
            "opensearch": args.opensearch_url,
        },
        "cases": [],
        "summary": {
            "passed": 0,
            "failed": 0,
        },
    }

    exit_code = 0
    for case in fixture.get("cases", []):
        steelsearch = request_response(args.steelsearch_url, case, args.timeout)
        opensearch = request_response(args.opensearch_url, case, args.timeout)
        errors = (
            check_target(case, steelsearch)
            + check_target(case, opensearch)
            + compare_targets(case, steelsearch, opensearch)
        )
        status = "passed" if not errors else "failed"
        if errors:
            exit_code = 1
            report["summary"]["failed"] += 1
        else:
            report["summary"]["passed"] += 1
        report["cases"].append(
            {
                "name": case["name"],
                "status": status,
                "steelsearch": steelsearch,
                "opensearch": opensearch,
                "errors": errors,
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
