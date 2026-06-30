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

from search_compat import extract as extract_compat_response


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "vector-search-compat.json"
DEFAULT_OUTPUT = ROOT / "target" / "vector-search-compat-report.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument(
        "--steelsearch-only",
        action="store_true",
        help="run executable Steelsearch vector checks without an OpenSearch k-NN plugin target",
    )
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
    summary = {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
    }
    if response.get("status") != 200:
        error = normalized_error_body(body)
        summary["error_type"] = error.get("type")
        summary["error_reason"] = error.get("reason")
        caused_by = error.get("caused_by") or {}
        if caused_by:
            summary["caused_by_type"] = caused_by.get("type")
            summary["caused_by_reason"] = caused_by.get("reason")
    return summary


def normalized_error_body(body: dict[str, Any]) -> dict[str, Any]:
    error = body.get("error") or {}
    if isinstance(error, dict):
        return error
    if isinstance(error, str):
        return {"type": None, "reason": error}
    return {"type": None, "reason": str(error)}


def error_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    error = normalized_error_body(body)
    summary = {
        "status": response.get("status"),
        "error_type": error.get("type"),
        "error_reason": error.get("reason"),
    }
    root_cause = error.get("root_cause")
    if isinstance(root_cause, list) and root_cause:
        first = root_cause[0]
        if isinstance(first, dict):
            summary["root_cause_type"] = first.get("type")
            summary["root_cause_reason"] = first.get("reason")
    return summary


def summarize_response(kind: str, response: dict[str, Any]) -> dict[str, Any]:
    if kind == "error_shape":
        return error_summary(response)
    if kind == "search_summary":
        return search_summary(response)
    return extract_compat_response(kind, response)


def case_report_base(case: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {"name": case["name"]}
    for key in ("metadata", "evidence_class", "evidence_classes"):
        if key in case:
            result[key] = case[key]
    return result


def missing_knn_plugin_response(response: dict[str, Any]) -> bool:
    body = response.get("body") or {}
    error = normalized_error_body(body)
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
    delete_index = {
        "name": "delete_index",
        **request_json(base_url, "DELETE", f"/{index}", None, timeout),
    }
    reports.append(delete_index)
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


def run_case_request(
    base_url: str,
    fixture: dict[str, Any],
    case: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    steps = []
    if "steps" not in case:
        path = case.get("path", f"/{fixture['index']}/_search")
        response = request_json(
            base_url,
            case.get("method", "POST"),
            path,
            case.get("body"),
            timeout,
        )
        return response, steps

    response: dict[str, Any] = {"status": 0, "body": None, "body_text": ""}
    for step in case["steps"]:
        response = request_json(
            base_url,
            step.get("method", "POST"),
            step["path"].replace("${index}", fixture["index"]),
            step.get("body"),
            timeout,
        )
        extract_kind = step.get("extract", case.get("kind", case.get("extract", "search_summary")))
        expected_status = step.get("expected_status", 200)
        status = response.get("status")
        steps.append(
            {
                "name": step.get("name"),
                "status": status,
                "expected_status": expected_status,
                "passed": status == expected_status,
                "extract": summarize_response(extract_kind, response),
            }
        )
    return response, steps


def compare_case_result(
    case: dict[str, Any],
    fixture: dict[str, Any],
    base_url: str,
    timeout: float,
) -> dict[str, Any]:
    response, steps = run_case_request(base_url, fixture, case, timeout)
    compare_step_name = case.get("compare_step")
    compare_step = None
    if isinstance(compare_step_name, str):
        compare_step = next((step for step in steps if step.get("name") == compare_step_name), None)
    kind = case.get("extract", case.get("kind", "search_summary"))
    summary = compare_step["extract"] if compare_step else summarize_response(kind, response)
    result = {
        "status": compare_step.get("status") if compare_step else response.get("status"),
        "extract": summary,
        "raw_response": response.get("body"),
    }
    if steps:
        result["steps"] = steps
        result["step_failed"] = any(not step.get("passed", True) for step in steps)
    if isinstance(compare_step_name, str) and compare_step is None:
        result["step_failed"] = True
        result["missing_compare_step"] = compare_step_name
    return result


def expected_case_status(case: dict[str, Any]) -> int:
    if isinstance(case.get("expected_status"), int):
        return int(case["expected_status"])
    if case.get("kind") == "error_shape" or case.get("extract") == "error_shape":
        return 400
    return 200


def steelsearch_only_case_result(
    case: dict[str, Any],
    fixture: dict[str, Any],
    base_url: str,
    timeout: float,
) -> dict[str, Any]:
    steelsearch = compare_case_result(case, fixture, base_url, timeout)
    errors = []
    expected_status = expected_case_status(case)
    if steelsearch.get("status") != expected_status:
        errors.append(
            f"steelsearch status drift: expected={expected_status} actual={steelsearch.get('status')}"
        )
    if steelsearch.get("step_failed"):
        errors.append(f"steelsearch step failure: {steelsearch.get('steps')!r}")
    status = "passed" if not errors else "failed"
    result = case_report_base(case)
    result.update(
        {
            "status": status,
            "steelsearch": steelsearch["extract"],
            "steelsearch_steps": steelsearch.get("steps", []),
            "errors": errors,
        }
    )
    return result


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url:
        print("STEELSEARCH_URL is required", file=sys.stderr)
        return 2
    if not args.opensearch_url:
        args.steelsearch_only = True

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    steelsearch_setup, steelsearch_degraded = seed_target(args.steelsearch_url, fixture, args.timeout)
    opensearch_setup: list[dict[str, Any]] = []
    opensearch_degraded = None
    if args.opensearch_url:
        opensearch_setup, opensearch_degraded = seed_target(args.opensearch_url, fixture, args.timeout)
    degraded_reason = steelsearch_degraded or opensearch_degraded
    steelsearch_only = args.steelsearch_only or not args.opensearch_url

    report: dict[str, Any] = {
        "name": "vector-search-compat",
        "fixture": str(Path(args.fixture).resolve()),
        "targets": {
            "steelsearch": args.steelsearch_url,
        },
        "setup": {
            "steelsearch": steelsearch_setup,
        },
        "cases": [],
        "summary": {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
        },
    }
    if args.opensearch_url:
        report["targets"]["opensearch"] = args.opensearch_url
        report["setup"]["opensearch"] = opensearch_setup
    if steelsearch_only:
        report["mode"] = "steelsearch_only"

    exit_code = 0
    for case in fixture["cases"]:
        if steelsearch_only:
            result = steelsearch_only_case_result(case, fixture, args.steelsearch_url, args.timeout)
            if result["status"] == "passed":
                report["summary"]["passed"] += 1
            else:
                exit_code = 1
                report["summary"]["failed"] += 1
            report["cases"].append(result)
            continue

        steelsearch = compare_case_result(case, fixture, args.steelsearch_url, args.timeout)
        assert args.opensearch_url is not None
        opensearch = compare_case_result(case, fixture, args.opensearch_url, args.timeout)
        if degraded_reason is not None:
            report["summary"]["skipped"] += 1
            result = case_report_base(case)
            result.update(
                {
                    "status": "skipped",
                    "steelsearch": steelsearch["extract"],
                    "opensearch": opensearch["extract"],
                    "errors": [],
                    "skipped_reason": degraded_reason,
                }
            )
            report["cases"].append(result)
            continue
        steel_summary = steelsearch["extract"]
        open_summary = opensearch["extract"]
        errors = []
        if steelsearch.get("step_failed"):
            errors.append(f"steelsearch step failure: {steelsearch.get('steps')!r}")
        if opensearch.get("step_failed"):
            errors.append(f"opensearch step failure: {opensearch.get('steps')!r}")
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
        result = case_report_base(case)
        result.update(
            {
                "status": status,
                "steelsearch": steel_summary,
                "opensearch": open_summary,
                "steelsearch_steps": steelsearch.get("steps", []),
                "opensearch_steps": opensearch.get("steps", []),
                "errors": errors,
            }
        )
        report["cases"].append(result)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
