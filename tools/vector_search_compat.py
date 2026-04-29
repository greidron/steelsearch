#!/usr/bin/env python3
"""Run bounded vector/hybrid search compatibility checks against Steelsearch and OpenSearch."""

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
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "vector-search-compat.json"
DEFAULT_OUTPUT = ROOT / "target" / "vector-search-compat-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument(
        "--output",
        default=os.environ.get("VECTOR_SEARCH_COMPAT_REPORT", str(DEFAULT_OUTPUT)),
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
    return {"status": status, "body": body, "body_text": text}


def put_doc(base_url: str, index: str, doc_id: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    return request_json(
        base_url,
        "PUT",
        f"/{index}/_doc/{doc_id}?refresh=wait_for",
        body,
        timeout,
    )


def search_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
    }


def error_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    error = body.get("error") or {}
    return {
        "status": response.get("status"),
        "error_type": error.get("type"),
    }


def missing_knn_plugin_response(response: dict[str, Any]) -> bool:
    body = response.get("body") or {}
    error = body.get("error") or {}
    reason = str(error.get("reason") or "")
    caused_by_reason = str((error.get("caused_by") or {}).get("reason") or "")
    return (
        response.get("status") == 400
        and (
            (
                error.get("type") == "settings_exception"
                and "unknown setting [index.knn]" in reason
            )
            or (
                error.get("type") == "mapper_parsing_exception"
                and "No handler for type [knn_vector]" in f"{reason} {caused_by_reason}"
            )
        )
    )


def seed_target(base_url: str, fixture: dict[str, Any], timeout: float) -> tuple[list[dict[str, Any]], str | None]:
    index = fixture["index"]
    reports = []
    create_index = {
        "name": "create_index",
        **request_json(
            base_url,
            "PUT",
            f"/{index}",
            {
                "settings": fixture["settings"],
                "mappings": fixture["mappings"],
            },
            timeout,
        ),
    }
    reports.append(create_index)
    if missing_knn_plugin_response(create_index):
        return reports, "opensearch target does not expose the k-NN plugin surface required by the fixture"
    for entry in fixture["docs"]:
        reports.append(
            {
                "name": f"put_doc_{entry['id']}",
                **put_doc(base_url, index, entry["id"], entry["source"], timeout),
            }
        )
    return reports, None


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url or not args.opensearch_url:
        print("Both STEELSEARCH_URL and OPENSEARCH_URL are required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    steelsearch_setup, steelsearch_degraded = seed_target(args.steelsearch_url, fixture, args.timeout)
    opensearch_setup, opensearch_degraded = seed_target(args.opensearch_url, fixture, args.timeout)
    degraded_reason = steelsearch_degraded or opensearch_degraded

    report: dict[str, Any] = {
        "name": "vector-search-compat",
        "fixture": str(Path(args.fixture).resolve()),
        "targets": {
            "steelsearch": args.steelsearch_url,
            "opensearch": args.opensearch_url,
        },
        "setup": {
            "steelsearch": steelsearch_setup,
            "opensearch": opensearch_setup,
        },
        "cases": [],
        "summary": {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
    }

    exit_code = 0
    for case in fixture["cases"]:
        path = case.get("path", f"/{fixture['index']}/_search")
        method = case.get("method", "POST")
        steelsearch = request_json(
            args.steelsearch_url,
            method,
            path,
            case["body"],
            args.timeout,
        )
        opensearch = request_json(
            args.opensearch_url,
            method,
            path,
            case["body"],
            args.timeout,
        )
        if degraded_reason is not None:
            report["summary"]["skipped"] += 1
            report["cases"].append(
                {
                    "name": case["name"],
                    "status": "skipped",
                    "steelsearch": search_summary(steelsearch)
                    if case.get("kind", "search_summary") != "error_shape"
                    else error_summary(steelsearch),
                    "opensearch": search_summary(opensearch)
                    if case.get("kind", "search_summary") != "error_shape"
                    else error_summary(opensearch),
                    "errors": [],
                    "skipped_reason": degraded_reason,
                }
            )
            continue
        kind = case.get("kind", "search_summary")
        if kind == "error_shape":
            steel_summary = error_summary(steelsearch)
            open_summary = error_summary(opensearch)
        else:
            steel_summary = search_summary(steelsearch)
            open_summary = search_summary(opensearch)
        errors = []
        if steel_summary != open_summary:
            errors.append(
                f"search summary drift: steelsearch={steel_summary!r} opensearch={open_summary!r}"
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
                "steelsearch": steel_summary,
                "opensearch": open_summary,
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
