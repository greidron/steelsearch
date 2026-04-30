#!/usr/bin/env python3
"""Run a strict Steelsearch-only ML model surface compatibility fixture."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "ml-model-surface-compat.json"
DEFAULT_OUTPUT = ROOT / "target" / "ml-model-surface-compat-report.json"
PLACEHOLDER = re.compile(r"\$\{([^}]+)\}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=os.environ.get("ML_MODEL_SURFACE_COMPAT_REPORT", str(DEFAULT_OUTPUT)))
    parser.add_argument("--timeout", type=float, default=30.0)
    return parser.parse_args()


def request_json(base_url: str, method: str, path: str, body: Any | None, timeout: float) -> dict[str, Any]:
    payload = None if body is None else json.dumps(body).encode("utf-8")
    request = urllib.request.Request(base_url.rstrip("/") + path, data=payload, method=method)
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
    return {"status": status, "body": body, "body_text": text}


def extract_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split('.'):
        if isinstance(current, list):
            if not token.isdigit() or int(token) >= len(current):
                return None
            current = current[int(token)]
            continue
        if not isinstance(current, dict) or token not in current:
            return None
        current = current[token]
    return current


def resolve_placeholders(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, str):
        match = PLACEHOLDER.fullmatch(value)
        if match:
            case_name, path = match.group(1).split('.', 1)
            return extract_path(results.get(case_name, {}).get('body'), path)
        return PLACEHOLDER.sub(
            lambda placeholder: str(
                extract_path(
                    results.get(placeholder.group(1).split('.', 1)[0], {}).get('body'),
                    placeholder.group(1).split('.', 1)[1],
                )
            ),
            value,
        )
    if isinstance(value, list):
        return [resolve_placeholders(item, results) for item in value]
    if isinstance(value, dict):
        return {key: resolve_placeholders(item, results) for key, item in value.items()}
    return value


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url:
        print("STEELSEARCH_URL is required", file=sys.stderr)
        return 2
    fixture = json.loads(Path(args.fixture).read_text(encoding='utf-8'))
    results: dict[str, dict[str, Any]] = {}
    report = {"name": fixture.get("name", "ml-model-surface-compat"), "fixture": str(Path(args.fixture).resolve()), "target": args.steelsearch_url, "cases": [], "summary": {"passed": 0, "failed": 0}}
    exit_code = 0
    for case in fixture["cases"]:
        path = resolve_placeholders(case["path"], results)
        body = resolve_placeholders(case.get("body"), results)
        response = request_json(args.steelsearch_url, case["method"], path, body, args.timeout)
        results[case["name"]] = response
        errors = []
        if response["status"] != case["expected_status"]:
            errors.append(f"status drift: expected={case['expected_status']} actual={response['status']}")
        summary = {"status": response["status"]}
        for compare_path in case.get("compare_paths", []):
            actual = extract_path(response.get("body"), compare_path)
            expected = resolve_placeholders(case["expected_paths"][compare_path], results)
            summary[compare_path] = actual
            if actual != expected:
                errors.append(f"path drift {compare_path}: expected={expected!r} actual={actual!r}")
        status = "passed" if not errors else "failed"
        report["summary"][status] += 1
        if errors:
            exit_code = 1
        report["cases"].append({"name": case["name"], "status": status, "response": summary, "errors": errors})
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
