#!/usr/bin/env python3
"""Run native-closure validation sub-batches and preserve failed case details."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]


def parse_payload(output: str) -> dict[str, Any]:
    start = output.find("{")
    if start < 0:
        raise ValueError("validation output did not contain a JSON object")
    return json.loads(output[start:])


def failed_cases(payload: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for result in payload.get("results", []):
        if result.get("ok") is True and result.get("status") == "ok":
            continue
        cases.append({
            "name": result.get("name"),
            "group": result.get("group"),
            "status": result.get("status"),
            "returncode": result.get("returncode"),
        })
    return cases


def run_batch(batch: str) -> dict[str, Any]:
    command = [
        sys.executable,
        "tools/run-native-closure-validation.py",
        "--batch",
        batch,
        "--format",
        "json",
    ]
    result = subprocess.run(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    try:
        payload = parse_payload(result.stdout)
    except (json.JSONDecodeError, ValueError) as exc:
        return {
            "test_count": 0,
            "failed_count": 1,
            "zero_test_count": 0,
            "returncode": result.returncode,
            "parse_error": str(exc),
            "stdout_tail": result.stdout[-4000:],
        }

    summary = payload.get("summary", {})
    cases = failed_cases(payload)
    test_names = [
        f"{result.get('group')}:{result.get('name')}"
        for result in payload.get("results", [])
        if isinstance(result, dict)
        and isinstance(result.get("group"), str)
        and result.get("group")
        and isinstance(result.get("name"), str)
        and result.get("name")
    ]
    return {
        "test_count": summary.get("test_count"),
        "test_name_count": len(test_names),
        "test_name_digest": hashlib.sha256(
            ("\n".join(test_names) + "\n").encode()
        ).hexdigest(),
        "failed_count": summary.get("failed_count"),
        "zero_test_count": summary.get("zero_test_count"),
        "returncode": result.returncode,
        "failed_cases": cases,
    }


def batch_passed(summary: dict[str, Any]) -> bool:
    return (
        summary.get("returncode") == 0
        and summary.get("failed_count") == 0
        and summary.get("test_count", 0) > 0
        and summary.get("zero_test_count") == 0
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batches", nargs="+", help="Batch names to run in order.")
    args = parser.parse_args()

    summaries = {batch: run_batch(batch) for batch in args.batches}
    failed_batches = [
        {
            "batch": batch,
            "failed_count": summary.get("failed_count"),
            "failed_cases": summary.get("failed_cases", []),
            "returncode": summary.get("returncode"),
        }
        for batch, summary in summaries.items()
        if not batch_passed(summary)
    ]
    passed = not failed_batches
    print(json.dumps({
        "summary": {
            "passed": passed,
            "batches": summaries,
            "failed_batches": failed_batches,
        }
    }))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
