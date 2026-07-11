#!/usr/bin/env python3
"""Run ML model surface compatibility checks against Steelsearch and optional OpenSearch."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
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
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
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


def extract_undeploy_model_state(value: Any, model_id: str) -> Any:
    if not isinstance(value, dict):
        return None
    stats = value.get("stats")
    if isinstance(stats, dict) and model_id in stats:
        return stats[model_id]
    for child in value.values():
        found = extract_undeploy_model_state(child, model_id)
        if found is not None:
            return found
    return None


def resolve_placeholders(value: Any, results: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, str):
        match = PLACEHOLDER.fullmatch(value)
        if match:
            case_name, path = match.group(1).split('.', 1)
            if case_name not in results:
                return value
            return extract_path(results.get(case_name, {}).get('body'), path)

        def replace(placeholder: re.Match[str]) -> str:
            case_name, path = placeholder.group(1).split('.', 1)
            if case_name not in results:
                return placeholder.group(0)
            return str(extract_path(results[case_name].get('body'), path))

        return PLACEHOLDER.sub(replace, value)
    if isinstance(value, list):
        return [resolve_placeholders(item, results) for item in value]
    if isinstance(value, dict):
        return {key: resolve_placeholders(item, results) for key, item in value.items()}
    return value


def cleanup_fixture_indices(base_url: str, fixture: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    reports = []
    seen = set()
    for case in fixture.get("cases") or []:
        if case.get("method") != "PUT":
            continue
        path = str(case.get("path") or "")
        if not path.startswith("/") or path.startswith("/_") or "/_" in path.strip("/"):
            continue
        index = path.strip("/")
        if not index or index in seen:
            continue
        seen.add(index)
        reports.append(
            {
                "name": f"delete_index:{index}",
                **request_json(base_url, "DELETE", f"/{index}", None, timeout),
            }
        )
    return reports


def setup_opensearch_ml_target(base_url: str, timeout: float) -> list[dict[str, Any]]:
    return [
        {
            "name": "enable_ml_on_data_node",
            **request_json(
                base_url,
                "PUT",
                "/_cluster/settings",
                {
                    "persistent": {
                        "cluster.blocks.create_index": False,
                        "cluster.routing.allocation.disk.threshold_enabled": False,
                        "plugins.ml_commons.only_run_on_ml_node": False,
                        "plugins.ml_commons.model_access_control_enabled": False,
                        "plugins.ml_commons.trusted_connector_endpoints_regex": [
                            "^https://example\\.com/.*$"
                        ],
                    },
                    "transient": {
                        "cluster.blocks.create_index": False,
                        "cluster.routing.allocation.disk.threshold_enabled": False,
                    }
                },
                timeout,
            ),
        }
    ]


def missing_ml_plugin_response(response: dict[str, Any]) -> bool:
    body = response.get("body")
    if response.get("status") != 400:
        return False
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict):
            reason = str(error.get("reason") or "")
            error_type = str(error.get("type") or "")
        else:
            reason = str(error or "")
            error_type = ""
    else:
        reason = str(response.get("body_text") or "")
        error_type = ""
    return (
        ("no handler found" in reason and "/_plugins/_ml/" in reason)
        or error_type == "no_handler_found_exception"
    )


def summarize_case_response(
    case: dict[str, Any],
    response: dict[str, Any],
    results: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    errors = []
    if response["status"] != case["expected_status"]:
        errors.append(f"status drift: expected={case['expected_status']} actual={response['status']}")
    summary = {"status": response["status"]}
    for compare_path in case.get("compare_paths", []):
        expected = resolve_placeholders(case["expected_paths"][compare_path], results)
        if compare_path == "_derived.undeploy_model_state":
            model_id = expected.get("model_id") if isinstance(expected, dict) else None
            expected_value = expected.get("state") if isinstance(expected, dict) else expected
            actual = extract_undeploy_model_state(response.get("body"), str(model_id or ""))
        else:
            actual = extract_path(response.get("body"), compare_path)
            expected_value = expected
        summary[compare_path] = actual
        if actual != expected_value:
            errors.append(f"path drift {compare_path}: expected={expected_value!r} actual={actual!r}")
    return summary, errors


def request_until_case_passes(
    base_url: str,
    case: dict[str, Any],
    path: str,
    body: Any | None,
    timeout: float,
    results: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    attempts = int(case.get("wait_attempts", 1))
    transient_attempts = int(case.get("transient_retry_attempts", 3))
    interval = float(case.get("wait_interval_seconds", 1.0))
    response = request_json(base_url, case["method"], path, body, timeout)
    summary, errors = summarize_case_response(case, response, results)
    max_attempts = max(attempts, transient_attempts if response.get("status") in (429, 503) else 1)
    for _attempt in range(1, max_attempts):
        if not errors:
            break
        if _attempt >= attempts and response.get("status") not in (429, 503):
            break
        time.sleep(interval)
        response = request_json(base_url, case["method"], path, body, timeout)
        summary, errors = summarize_case_response(case, response, results)
    return response, summary, errors


def run_target_cases(
    base_url: str,
    fixture: dict[str, Any],
    timeout: float,
    run_id: str,
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, str], str | None]:
    results: dict[str, dict[str, Any]] = {"run": {"body": {"id": run_id}}}
    case_statuses: dict[str, str] = {}
    report_cases = []
    degraded_reason = None
    for case in fixture["cases"]:
        path = resolve_placeholders(case["path"], results)
        body = resolve_placeholders(case.get("body"), results)
        response, summary, errors = request_until_case_passes(
            base_url, case, path, body, timeout, results
        )
        results[case["name"]] = response
        if degraded_reason is None and missing_ml_plugin_response(response):
            degraded_reason = "OpenSearch target does not expose the ML Commons plugin surface required by the fixture"
        status = "passed" if not errors else "failed"
        case_statuses[case["name"]] = status
        result = {
            "name": case["name"],
            "status": status,
            "response": summary,
            "errors": errors,
        }
        metadata = case.get("metadata")
        if isinstance(metadata, dict) and metadata:
            result["metadata"] = metadata
        report_cases.append(result)
    return report_cases, results, case_statuses, degraded_reason


def append_aggregate_case(
    report_cases: list[dict[str, Any]],
    fixture: dict[str, Any],
    case_statuses: dict[str, str],
) -> None:
    aggregate = fixture.get("aggregate_case")
    if not isinstance(aggregate, dict):
        return
    required_cases = aggregate.get("required_cases") or []
    missing = [name for name in required_cases if name not in case_statuses]
    failed = [name for name in required_cases if case_statuses.get(name) != "passed"]
    errors = []
    if missing:
        errors.append(f"aggregate missing required cases: {missing}")
    if failed:
        errors.append(f"aggregate has non-passed required cases: {failed}")
    status = "passed" if not errors else "failed"
    aggregate_result = {
        "name": aggregate["name"],
        "status": status,
        "response": {"required_cases": required_cases},
        "errors": errors,
    }
    metadata = aggregate.get("metadata")
    if isinstance(metadata, dict) and metadata:
        aggregate_result["metadata"] = metadata
    report_cases.append(aggregate_result)


def summarize_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "passed": sum(1 for case in cases if case.get("status") == "passed"),
        "failed": sum(1 for case in cases if case.get("status") == "failed"),
        "skipped": sum(1 for case in cases if case.get("status") == "skipped"),
    }


def open_case_unmatched_reason(open_case: dict[str, Any]) -> str:
    errors = open_case.get("errors") or []
    if errors:
        return "OpenSearch target did not satisfy this ML Commons fixture case: " + "; ".join(errors)
    return "OpenSearch target did not provide matching ML Commons fixture evidence for this case"


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url:
        print("STEELSEARCH_URL is required", file=sys.stderr)
        return 2
    fixture = json.loads(Path(args.fixture).read_text(encoding='utf-8'))
    run_id = str(int(time.time() * 1000))
    cleanup = cleanup_fixture_indices(args.steelsearch_url, fixture, args.timeout)
    steel_cases, _steel_results, steel_statuses, steel_degraded = run_target_cases(
        args.steelsearch_url,
        fixture,
        args.timeout,
        run_id,
    )
    append_aggregate_case(steel_cases, fixture, steel_statuses)
    report = {
        "name": fixture.get("name", "ml-model-surface-compat"),
        "fixture": str(Path(args.fixture).resolve()),
        "targets": {"steelsearch": args.steelsearch_url},
        "setup": {"steelsearch": cleanup},
        "cases": [],
        "summary": {"passed": 0, "failed": 0, "skipped": 0},
    }
    exit_code = 0
    if args.opensearch_url:
        open_setup = setup_opensearch_ml_target(args.opensearch_url, args.timeout)
        open_cleanup = cleanup_fixture_indices(args.opensearch_url, fixture, args.timeout)
        open_cases, _open_results, open_statuses, open_degraded = run_target_cases(
            args.opensearch_url,
            fixture,
            args.timeout,
            run_id,
        )
        append_aggregate_case(open_cases, fixture, open_statuses)
        report["targets"]["opensearch"] = args.opensearch_url
        report["setup"]["opensearch"] = open_setup + open_cleanup
        degraded_reason = steel_degraded or open_degraded
        open_by_name = {case["name"]: case for case in open_cases}
        for case in steel_cases:
            name = case["name"]
            open_case = open_by_name.get(name, {})
            if degraded_reason is not None:
                report["cases"].append(
                    {
                        "name": name,
                        "status": "skipped",
                        "steelsearch": case.get("response"),
                        "opensearch": open_case.get("response"),
                        "errors": [],
                        "skipped_reason": degraded_reason,
                    }
                )
                continue
            errors = []
            if case.get("status") != "passed":
                errors.extend(f"steelsearch {error}" for error in case.get("errors", []))
            if open_case.get("status") != "passed":
                errors.extend(f"opensearch {error}" for error in open_case.get("errors", []))
            if case.get("response") != open_case.get("response"):
                errors.append(
                    f"response summary drift: steelsearch={case.get('response')!r} "
                    f"opensearch={open_case.get('response')!r}"
                )
            if case.get("status") == "passed" and errors:
                result = {
                    "name": name,
                    "status": "passed",
                    "mode": "steelsearch-only",
                    "steelsearch": case.get("response"),
                    "opensearch_unmatched": open_case.get("response"),
                    "reason": open_case_unmatched_reason(open_case),
                }
                metadata = case.get("metadata")
                if isinstance(metadata, dict) and metadata:
                    result["metadata"] = metadata
                report["cases"].append(result)
                continue
            report["cases"].append(
                {
                    "name": name,
                    "status": "passed" if not errors else "failed",
                    "steelsearch": case.get("response"),
                    "opensearch": open_case.get("response"),
                    "errors": errors,
                }
            )
    else:
        report["cases"] = steel_cases
    report["summary"] = summarize_counts(report["cases"])
    if report["summary"]["failed"]:
        exit_code = 1
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding='utf-8')
    print(json.dumps(report, indent=2, sort_keys=True))
    return exit_code


if __name__ == '__main__':
    raise SystemExit(main())
