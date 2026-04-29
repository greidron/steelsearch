#!/usr/bin/env python3
"""Run Steelsearch-only multi-node transport/admin integration checks."""

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
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "multi-node-transport-admin.json"
DEFAULT_OUTPUT = ROOT / "target" / "multi-node-transport-admin-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--node-a-url", default=os.environ.get("STEELSEARCH_NODE_A_URL"))
    parser.add_argument("--node-b-url", default=os.environ.get("STEELSEARCH_NODE_B_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--output",
        default=os.environ.get("MULTI_NODE_TRANSPORT_ADMIN_REPORT", str(DEFAULT_OUTPUT)),
    )
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args()


def request_response(base_url: str, case: dict[str, Any], timeout: float) -> dict[str, Any]:
    request = urllib.request.Request(
        base_url.rstrip("/") + case["path"],
        method=case["method"],
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read()
            return decode_response(response.status, payload)
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
    return errors


def main() -> int:
    args = parse_args()
    if not args.node_a_url or not args.node_b_url:
        print(
            "Both STEELSEARCH_NODE_A_URL and STEELSEARCH_NODE_B_URL are required",
            file=sys.stderr,
        )
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    targets = {
        "node_a": args.node_a_url,
        "node_b": args.node_b_url,
    }
    report: dict[str, Any] = {
        "name": fixture.get("name", "multi-node-transport-admin"),
        "fixture": str(Path(args.fixture).resolve()),
        "targets": targets,
        "cases": [],
        "summary": {
            "passed": 0,
            "failed": 0,
        },
    }

    exit_code = 0
    for case in fixture.get("cases", []):
        response = request_response(targets[case["target"]], case, args.timeout)
        errors = check_case(case, response)
        status = "passed" if not errors else "failed"
        if errors:
            exit_code = 1
            report["summary"]["failed"] += 1
        else:
            report["summary"]["passed"] += 1
        report["cases"].append(
            {
                "name": case["name"],
                "target": case["target"],
                "status": status,
                "response": response,
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
