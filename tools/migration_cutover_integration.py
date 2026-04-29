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


def search_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
    }


def put_doc(base_url: str, index: str, doc_id: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    return request_json(
        base_url,
        "PUT",
        f"/{index}/_doc/{doc_id}?refresh=wait_for",
        body,
        timeout,
    )


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url or not args.opensearch_url:
        print("Both STEELSEARCH_URL and OPENSEARCH_URL are required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    index = fixture["index"]
    mappings = fixture["mappings"]
    settings = fixture["settings"]
    docs = fixture["docs"]
    query = fixture["query"]

    report: dict[str, Any] = {
        "name": "migration-cutover-integration",
        "fixture": str(Path(args.fixture).resolve()),
        "source": args.opensearch_url,
        "target": args.steelsearch_url,
        "steps": [],
        "comparison": {},
    }

    source_create = request_json(
        args.opensearch_url,
        "PUT",
        f"/{index}",
        {
            "settings": settings,
            "mappings": mappings,
        },
        args.timeout,
    )
    report["steps"].append({"name": "source_create", **source_create})

    for entry in docs:
        source_put = put_doc(
            args.opensearch_url,
            index,
            entry["id"],
            entry["source"],
            args.timeout,
        )
        report["steps"].append({"name": f"source_put_{entry['id']}", **source_put})

    source_mapping = request_json(
        args.opensearch_url,
        "GET",
        f"/{index}/_mapping",
        None,
        args.timeout,
    )
    source_settings = request_json(
        args.opensearch_url,
        "GET",
        f"/{index}/_settings",
        None,
        args.timeout,
    )
    source_search = request_json(
        args.opensearch_url,
        "POST",
        f"/{index}/_search",
        query,
        args.timeout,
    )
    report["steps"].append({"name": "source_mapping", **source_mapping})
    report["steps"].append({"name": "source_settings", **source_settings})
    report["steps"].append({"name": "source_search", **source_search})

    target_create = request_json(
        args.steelsearch_url,
        "PUT",
        f"/{index}",
        {
            "settings": settings,
            "mappings": mappings,
        },
        args.timeout,
    )
    report["steps"].append({"name": "target_create", **target_create})

    for entry in docs:
        target_put = put_doc(
            args.steelsearch_url,
            index,
            entry["id"],
            entry["source"],
            args.timeout,
        )
        report["steps"].append({"name": f"target_put_{entry['id']}", **target_put})

    target_search = request_json(
        args.steelsearch_url,
        "POST",
        f"/{index}/_search",
        query,
        args.timeout,
    )
    report["steps"].append({"name": "target_search", **target_search})

    source_summary = search_summary(source_search)
    target_summary = search_summary(target_search)
    report["comparison"] = {
        "source": source_summary,
        "target": target_summary,
        "match": source_summary == target_summary,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["comparison"]["match"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
