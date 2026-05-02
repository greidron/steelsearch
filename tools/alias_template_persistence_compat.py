#!/usr/bin/env python3
"""Run alias/template persistence compatibility fixtures.

The runner executes tools/fixtures/alias-template-persistence-compat.json
against Steelsearch and, when provided, OpenSearch. It compares only stable
fields documented by the fixture.
"""

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
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "alias-template-persistence-compat.json"
DEFAULT_OUTPUT = ROOT / "target" / "alias-template-persistence-compat-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--output", default=os.environ.get("ALIAS_TEMPLATE_COMPAT_REPORT", str(DEFAULT_OUTPUT)))
    parser.add_argument("--timeout", type=float, default=30.0)
    parser.add_argument("--no-reset", action="store_true", help="do not delete fixture resources before running")
    return parser.parse_args()


def request_json(base_url: str, request: dict[str, Any], timeout: float) -> dict[str, Any]:
    url = base_url.rstrip("/") + request["path"]
    body = request.get("body")
    data = None
    headers = {}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["content-type"] = "application/json"
    http_request = urllib.request.Request(
        url,
        data=data,
        method=request["method"],
        headers=headers,
    )
    try:
        with urllib.request.urlopen(http_request, timeout=timeout) as response:
            payload = response.read()
            return {
                "status": response.status,
                "body": json.loads(payload.decode("utf-8")) if payload else None,
            }
    except urllib.error.HTTPError as error:
        payload = error.read()
        try:
            body_payload = json.loads(payload.decode("utf-8")) if payload else None
        except json.JSONDecodeError:
            body_payload = payload.decode("utf-8", errors="replace")
        return {"status": error.code, "body": body_payload}
    except urllib.error.URLError as error:
        return {"status": None, "body": None, "error": str(error.reason)}


def cleanup_requests(fixture: dict[str, Any]) -> list[dict[str, Any]]:
    paths = {
        request["path"]
        for request in fixture["requests"]
        if request["method"] == "DELETE" and request["path"].startswith(("/_index_template/", "/"))
    }
    paths.update(
        {
            "/_component_template/steelsearch-live-component",
            "/_snapshot/steelsearch-persistence-repo/steelsearch-template-snapshot",
        }
    )
    return [
        {"name": f"cleanup_{index}", "method": "DELETE", "path": path}
        for index, path in enumerate(sorted(paths), start=1)
    ]


def run_target(
    name: str,
    base_url: str,
    fixture: dict[str, Any],
    timeout: float,
    reset: bool,
) -> dict[str, Any]:
    responses: dict[str, Any] = {}
    failures: list[dict[str, Any]] = []
    cleanup: dict[str, Any] = {}
    if reset:
        for request in cleanup_requests(fixture):
            response = request_json(base_url, request, timeout)
            cleanup[request["path"]] = response

    for request in fixture["requests"]:
        try:
            response = request_json(base_url, request, timeout)
            responses[request["name"]] = response
            status = response.get("status")
            if not isinstance(status, int) or status < 200 or status >= 300:
                failures.append(
                    {
                        "request": request["name"],
                        "status": status,
                        "error": response.get("error"),
                        "body": response.get("body"),
                    }
                )
        except Exception as error:  # noqa: BLE001 - report and continue with full context.
            failures.append({"request": request["name"], "error": str(error)})
            responses[request["name"]] = {"status": None, "body": None}
    return {
        "name": name,
        "url": base_url,
        "cleanup": cleanup,
        "failures": failures,
        "responses": responses,
        "stable": stable_fields(responses, fixture),
    }


def stable_fields(responses: dict[str, Any], fixture: dict[str, Any]) -> dict[str, Any]:
    stable: dict[str, Any] = {}
    source_requests = {
        "component_template_get": "get_component_template",
        "index_template_get": "get_index_template",
        "index_get": "get_index",
        "data_stream_get": "get_data_stream",
    }
    for section, request_name in source_requests.items():
        body = responses.get(request_name, {}).get("body")
        stable[section] = {
            path: extract_path(body, path)
            for path in fixture["stable_fields"].get(section, [])
        }

    stable["snapshot_restore"] = {
        "snapshot.state": extract_path(responses.get("create_snapshot", {}).get("body"), "snapshot.state"),
        "snapshot.indices": extract_path(responses.get("create_snapshot", {}).get("body"), "snapshot.indices"),
        "restored_component_template.name": extract_path(
            responses.get("get_restored_component_template", {}).get("body"),
            "component_templates[0].name",
        ),
        "restored_component_template.component_template.template.mappings.properties.component_field.type": extract_path(
            responses.get("get_restored_component_template", {}).get("body"),
            "component_templates[0].component_template.template.mappings.properties.component_field.type",
        ),
        "restored_template.name": extract_path(
            responses.get("get_restored_index_template", {}).get("body"),
            "index_templates[0].name",
        ),
        "restored_template.index_template.template.aliases.steelsearch-template-alias": extract_path(
            responses.get("get_restored_index_template", {}).get("body"),
            "index_templates[0].index_template.template.aliases.steelsearch-template-alias",
        ),
        "restored_index.settings.index.number_of_shards": extract_path(
            responses.get("get_restored_index", {}).get("body"),
            "steelsearch-template-000001.settings.index.number_of_shards",
        ),
        "restored_index.settings.index.number_of_replicas": extract_path(
            responses.get("get_restored_index", {}).get("body"),
            "steelsearch-template-000001.settings.index.number_of_replicas",
        ),
        "restored_index.mappings.properties.component_field.type": extract_path(
            responses.get("get_restored_index", {}).get("body"),
            "steelsearch-template-000001.mappings.properties.component_field.type",
        ),
        "restored_index.aliases": extract_path(
            responses.get("get_restored_index", {}).get("body"),
            "steelsearch-template-000001.aliases",
        ),
        "restored_data_stream.name": extract_path(
            responses.get("get_restored_data_stream", {}).get("body"),
            "data_streams[0].name",
        ),
        "restored_data_stream.template": extract_path(
            responses.get("get_restored_data_stream", {}).get("body"),
            "data_streams[0].template",
        ),
    }
    return stable


def extract_path(value: Any, path: str) -> Any:
    current = value
    for segment in path.split("."):
        if current is None:
            return None
        key, index = parse_segment(segment)
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return None
        if index is not None:
            if not isinstance(current, list) or index >= len(current):
                return None
            current = current[index]
    return current


def parse_segment(segment: str) -> tuple[str, int | None]:
    if segment.endswith("]") and "[" in segment:
        key, raw_index = segment[:-1].split("[", 1)
        return key, int(raw_index)
    return segment, None


def compare_stable(steelsearch: dict[str, Any], opensearch: dict[str, Any] | None) -> list[dict[str, Any]]:
    if opensearch is None:
        return []
    mismatches: list[dict[str, Any]] = []
    for section, steel_values in steelsearch["stable"].items():
        open_values = opensearch["stable"].get(section, {})
        for path, steel_value in steel_values.items():
            open_value = open_values.get(path)
            if steel_value != open_value:
                mismatches.append(
                    {
                        "section": section,
                        "path": path,
                        "steelsearch": steel_value,
                        "opensearch": open_value,
                    }
                )
    return mismatches


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url:
        print("STEELSEARCH_URL or --steelsearch-url is required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    reset = not args.no_reset
    report: dict[str, Any] = {
        "name": fixture.get("name", "alias-template-persistence-compat"),
        "fixture": str(Path(args.fixture).resolve()),
        "reset": reset,
        "targets": {},
        "mismatches": [],
    }
    steelsearch = run_target("steelsearch", args.steelsearch_url, fixture, args.timeout, reset)
    report["targets"]["steelsearch"] = steelsearch

    opensearch = None
    if args.opensearch_url:
        opensearch = run_target("opensearch", args.opensearch_url, fixture, args.timeout, reset)
        report["targets"]["opensearch"] = opensearch

    report["mismatches"] = compare_stable(steelsearch, opensearch)
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    Path(args.output).write_text(text, encoding="utf-8")
    print(text, end="")
    if steelsearch["failures"] or (opensearch and opensearch["failures"]) or report["mismatches"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
