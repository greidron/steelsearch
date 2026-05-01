#!/usr/bin/env python3
"""Run Steelsearch/OpenSearch HTTP compatibility fixtures.

The runner always exercises Steelsearch when STEELSEARCH_URL is available.
If OPENSEARCH_URL is also set, it applies the same fixture and compares
selected stable fields rather than volatile transport metadata.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "tools" / "fixtures" / "search-compat.json"
DEFAULT_REPORT = ROOT / "target" / "search-compat-report.json"
COMPAT_INDICES = {
    "logs-compat",
    "vectors-compat",
    "vectors-cosine-compat",
    "vectors-innerproduct-compat",
}
CAT_INDEX_REQUIRED_COLUMNS = {
    "health",
    "status",
    "index",
    "pri",
    "rep",
    "docs.count",
    "store.size",
}
CAT_ALIAS_REQUIRED_COLUMNS = {
    "alias",
    "index",
    "filter",
    "routing.index",
    "routing.search",
    "is_write_index",
}
CAT_HEALTH_REQUIRED_COLUMNS = {
    "epoch",
    "timestamp",
    "cluster",
    "status",
    "node.total",
    "node.data",
    "shards",
    "pri",
    "relo",
    "init",
    "unassign",
    "pending_tasks",
    "max_task_wait_time",
    "active_shards_percent",
}
CAT_NODES_REQUIRED_COLUMNS = {
    "ip",
    "node.role",
    "name",
}
CAT_NODEATTRS_REQUIRED_COLUMNS = {
    "node",
    "host",
    "ip",
    "attr",
    "value",
}
CAT_PENDING_TASKS_REQUIRED_COLUMNS = {
    "insertOrder",
    "timeInQueue",
    "priority",
    "source",
}
CAT_SHARDS_REQUIRED_COLUMNS = {
    "index",
    "shard",
    "prirep",
    "state",
    "docs",
    "store",
}
CAT_SEGMENTS_REQUIRED_COLUMNS = {
    "index",
    "shard",
    "prirep",
    "segment",
    "docs.count",
    "size",
}
CAT_PIT_SEGMENTS_REQUIRED_COLUMNS = {
    "index",
    "shard",
    "prirep",
    "segment",
    "docs.count",
    "size",
}
CAT_RECOVERY_REQUIRED_COLUMNS = {
    "index",
    "shard",
    "time",
    "type",
    "stage",
    "source_host",
    "source_node",
    "target_host",
    "target_node",
    "files",
    "files_recovered",
    "bytes",
    "bytes_recovered",
    "translog_ops",
    "translog_ops_recovered",
}
CAT_REPOSITORIES_REQUIRED_COLUMNS = {
    "id",
    "type",
}
CAT_SNAPSHOTS_REQUIRED_COLUMNS = {
    "id",
    "status",
    "start_epoch",
    "start_time",
    "end_epoch",
    "end_time",
    "duration",
    "indices",
    "successful_shards",
    "failed_shards",
    "total_shards",
}
CAT_TASKS_REQUIRED_COLUMNS = {
    "id",
    "action",
    "task_id",
    "parent_task_id",
    "type",
    "start_time",
    "timestamp",
    "running_time_ns",
    "running_time",
    "node_id",
    "ip",
    "port",
    "node",
    "version",
    "x_opaque_id",
}
CAT_TEMPLATES_REQUIRED_COLUMNS = {
    "name",
    "index_patterns",
    "order",
    "version",
    "composed_of",
}
CAT_THREAD_POOL_REQUIRED_COLUMNS = {
    "node_name",
    "name",
    "active",
    "queue",
    "rejected",
}
CAT_ALLOCATION_REQUIRED_COLUMNS = {
    "shards",
    "disk.indices",
    "disk.used",
    "disk.avail",
    "disk.total",
    "disk.percent",
    "host",
    "ip",
    "node",
}
CAT_FIELDDATA_REQUIRED_COLUMNS = {
    "id",
    "host",
    "ip",
    "node",
    "field",
    "size",
}
VOLATILE_RESPONSE_KEYS = {
    "_primary_term",
    "_seq_no",
    "_version",
    "build_date",
    "build_hash",
    "cluster_uuid",
    "node",
    "nodes",
    "primary_term",
    "seq_no",
    "start_time",
    "start_time_in_millis",
    "task",
    "task_id",
    "timestamp",
    "took",
}


def excluded_case_names() -> set[str]:
    raw = os.environ.get("SEARCH_COMPAT_EXCLUDE_CASES", "")
    return {name.strip() for name in raw.split(",") if name.strip()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", default=str(DEFAULT_FIXTURE))
    parser.add_argument("--report", default=str(DEFAULT_REPORT))
    parser.add_argument("--steelsearch-url", default=os.environ.get("STEELSEARCH_URL"))
    parser.add_argument("--opensearch-url", default=os.environ.get("OPENSEARCH_URL"))
    parser.add_argument("--timeout", type=float, default=10.0)
    parser.add_argument("--wait", action="store_true", help="wait for endpoints before running")
    args = parser.parse_args()

    if not args.steelsearch_url:
        print("STEELSEARCH_URL or --steelsearch-url is required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    excluded = excluded_case_names()
    if excluded:
        fixture["cases"] = [
            case for case in fixture["cases"] if case.get("name") not in excluded
        ]
    targets = {"steelsearch": args.steelsearch_url.rstrip("/")}
    if args.opensearch_url:
        targets["opensearch"] = args.opensearch_url.rstrip("/")

    report: dict[str, Any] = {
        "fixture": str(Path(args.fixture).resolve()),
        "targets": targets,
        "setup": [],
        "cases": [],
        "summary": {"passed": 0, "failed": 0, "skipped": 0, "by_area": {}, "skips": []},
    }

    if args.wait:
        for name, url in targets.items():
            wait_for_endpoint(name, url, args.timeout)

    for target_name, target_url in targets.items():
        report["setup"].extend(setup_target(target_name, target_url, fixture, args.timeout))

    for case in fixture["cases"]:
        result = run_case(case, targets, args.timeout)
        report["cases"].append(result)
        update_summary(report["summary"], result)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(
        "search compatibility: "
        f"{report['summary']['passed']} passed, "
        f"{report['summary']['failed']} failed, "
        f"{report['summary']['skipped']} skipped"
    )
    for area, area_summary in sorted(report["summary"]["by_area"].items()):
        print(
            f"  {area}: "
            f"{area_summary['passed']} passed, "
            f"{area_summary['failed']} failed, "
            f"{area_summary['skipped']} skipped"
        )
    for skipped in report["summary"]["skips"]:
        print(f"  skipped {skipped['name']}: {skipped['reason']}")
    print(f"report: {report_path}")
    return 1 if report["summary"]["failed"] else 0


def update_summary(summary: dict[str, Any], result: dict[str, Any]) -> None:
    status = result["status"]
    area = result["area"]
    summary[status] += 1
    by_area = summary["by_area"].setdefault(area, {"passed": 0, "failed": 0, "skipped": 0})
    by_area[status] += 1
    if status == "skipped":
        summary["skips"].append(
            {
                "name": result["name"],
                "area": area,
                "scope": result.get("skip_scope"),
                "reason": result.get("reason"),
            }
        )


def wait_for_endpoint(name: str, base_url: str, timeout: float) -> None:
    deadline = time.monotonic() + timeout
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            response = http_json(base_url, "GET", "/", None, timeout=2.0)
            if response["status"] < 500:
                return
        except Exception as error:  # noqa: BLE001 - endpoint probing preserves context
            last_error = error
        time.sleep(0.25)
    raise RuntimeError(f"{name} did not become ready at {base_url}: {last_error}")


def setup_target(target_name: str, base_url: str, fixture: dict[str, Any], timeout: float) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for index in fixture["indices"]:
        delete = http_json(base_url, "DELETE", f"/{index['name']}", None, timeout)
        if delete["status"] not in (200, 202, 404):
            steps.append(step_result(target_name, f"delete:{index['name']}", "failed", delete))
            continue
        steps.append(step_result(target_name, f"delete:{index['name']}", "passed", delete))

        create = http_json(base_url, "PUT", f"/{index['name']}", index["body"], timeout)
        create_status = status_for(create)
        if target_name == "opensearch" and missing_knn_plugin_response(create):
            create_status = "skipped"
            steps.append(
                step_result(
                    target_name,
                    f"create:{index['name']}",
                    create_status,
                    create,
                    skip_scope="degraded-source",
                    skipped_reason=(
                        "OpenSearch target does not expose the k-NN query/plugin surface in "
                        "this environment, so vector comparison is downgraded to degraded-source skip."
                    ),
                )
            )
            continue
        steps.append(step_result(target_name, f"create:{index['name']}", create_status, create))

    for batch in fixture["bulk"]:
        body = bulk_body(batch["index"], batch["documents"])
        bulk = http_json(base_url, "POST", f"/{batch['index']}/_bulk", body, timeout, raw=True)
        passed = 200 <= bulk["status"] < 300 and not bulk.get("body", {}).get("errors", True)
        steps.append(step_result(target_name, f"bulk:{batch['index']}", "passed" if passed else "failed", bulk))

    refresh = http_json(base_url, "POST", "/_refresh", {}, timeout)
    steps.append(step_result(target_name, "refresh:all", status_for(refresh), refresh))

    for alias in fixture.get("aliases", []):
        body = alias.get("body", {})
        put_alias = http_json(
            base_url,
            "PUT",
            f"/{alias['index']}/_alias/{alias['alias']}",
            body,
            timeout,
        )
        steps.append(
            step_result(
                target_name,
                f"alias:{alias['index']}:{alias['alias']}",
                status_for(put_alias),
                put_alias,
            )
        )
    for repository in fixture.get("repositories", []):
        body = resolve_fixture_placeholders(repository.get("body", {}))
        put_repository = http_json(
            base_url,
            "PUT",
            f"/_snapshot/{repository['name']}",
            body,
            timeout,
        )
        steps.append(
            step_result(
                target_name,
                f"repository:{repository['name']}",
                status_for(put_repository),
                put_repository,
            )
        )
    for template in fixture.get("legacy_templates", []):
        put_template = http_json(
            base_url,
            "PUT",
            f"/_template/{template['name']}",
            resolve_fixture_placeholders(template.get("body", {})),
            timeout,
        )
        steps.append(
            step_result(
                target_name,
                f"legacy_template:{template['name']}",
                status_for(put_template),
                put_template,
            )
        )
    for template in fixture.get("index_templates", []):
        put_template = http_json(
            base_url,
            "PUT",
            f"/_index_template/{template['name']}",
            resolve_fixture_placeholders(template.get("body", {})),
            timeout,
        )
        steps.append(
            step_result(
                target_name,
                f"index_template:{template['name']}",
                status_for(put_template),
                put_template,
            )
        )
    return steps


def resolve_fixture_placeholders(value: Any) -> Any:
    if isinstance(value, str):
        return os.path.expandvars(value)
    if isinstance(value, list):
        return [resolve_fixture_placeholders(item) for item in value]
    if isinstance(value, dict):
        return {key: resolve_fixture_placeholders(item) for key, item in value.items()}
    return value


def run_case(case: dict[str, Any], targets: dict[str, str], timeout: float) -> dict[str, Any]:
    target_results: dict[str, Any] = {}
    comparison_mode = case.get("comparison", "compare")
    selected_targets = targets
    if comparison_mode == "steelsearch_only":
        selected_targets = {"steelsearch": targets["steelsearch"]}

    for name, url in selected_targets.items():
        response, steps = run_case_request(url, case, timeout)
        target_results[name] = {
            "status": response["status"],
            "extract": extract(case["extract"], response),
            "raw_error": response.get("error"),
            "raw_response": raw_response(response),
            "normalized_response": normalized_response(response),
        }
        if steps:
            target_results[name]["steps"] = steps

    steel = target_results["steelsearch"]
    step_failed = any(
        not step.get("passed", True)
        for result in target_results.values()
        for step in result.get("steps", [])
    )
    if comparison_mode == "steelsearch_only" or "opensearch" not in target_results:
        expected_status = case.get("expected_steelsearch_status")
        passed = (
            steel["status"] == expected_status
            if expected_status is not None
            else steel["status"] < 500
        ) and not step_failed
        if comparison_mode == "steelsearch_only" and passed and "opensearch" in targets:
            status = "skipped"
        else:
            status = "passed" if passed else "failed"
        return {
            "name": case["name"],
            "area": case["area"],
            "status": status,
            "mode": comparison_mode.replace("_", "-") if comparison_mode != "compare" else "steelsearch-only",
            "targets": target_results,
            "expected_steelsearch_status": expected_status,
            "skip_scope": case.get("skip_scope", "opensearch-comparison") if status == "skipped" else None,
            "reason": case.get("reason"),
        }

    expected = target_results["opensearch"]
    if case["area"] == "knn" and missing_knn_query_response(expected["raw_response"]):
        return {
            "name": case["name"],
            "area": case["area"],
            "status": "skipped",
            "mode": "comparison",
            "targets": target_results,
            "skip_scope": "degraded-source",
            "reason": (
                "OpenSearch target does not expose the k-NN query/plugin surface in this "
                "environment, so vector comparison is downgraded to degraded-source skip."
            ),
        }
    if missing_runtime_mappings_support(expected["raw_response"]):
        return {
            "name": case["name"],
            "area": case["area"],
            "status": "skipped",
            "mode": "comparison",
            "targets": target_results,
            "skip_scope": "degraded-source",
            "reason": (
                "OpenSearch target does not expose request-body runtime_mappings in this "
                "environment, so runtime-fields comparison is downgraded to degraded-source skip."
            ),
        }
    matches = (
        steel["status"] == expected["status"]
        and steel["extract"] == expected["extract"]
        and not step_failed
    )
    return {
        "name": case["name"],
        "area": case["area"],
        "status": "passed" if matches else "failed",
        "mode": "comparison",
        "targets": target_results,
        "diff": None if matches else {"steelsearch": steel["extract"], "opensearch": expected["extract"]},
    }


def run_case_request(
    base_url: str,
    case: dict[str, Any],
    timeout: float,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    steps = case.get("steps")
    if not steps:
        response = http_json(
            base_url,
            case["method"],
            case["path"],
            case.get("body"),
            timeout,
            accept=case.get("accept"),
        )
        return response, []

    step_results: list[dict[str, Any]] = []
    response: dict[str, Any] = {"status": 0, "body": {}, "error": "case has no steps"}
    for index, step in enumerate(steps):
        resolved_step = resolve_step_placeholders(step, response)
        response = http_json(
            base_url,
            resolved_step["method"],
            resolved_step["path"],
            resolved_step.get("body"),
            timeout,
            raw=resolved_step.get("raw", False),
            accept=resolved_step.get("accept"),
        )
        expected_status = resolved_step.get("expected_status")
        step_results.append(
            {
                "name": resolved_step.get("name", f"step-{index + 1}"),
                "status": response["status"],
                "expected_status": expected_status,
                "passed": expected_status is None or response["status"] == expected_status,
                "extract": extract(resolved_step.get("extract", "status_only"), response),
            }
        )
    return response, step_results


def resolve_step_placeholders(step: dict[str, Any], previous_response: dict[str, Any]) -> dict[str, Any]:
    return resolve_placeholders(step, previous_response)


def resolve_placeholders(value: Any, previous_response: dict[str, Any]) -> Any:
    if isinstance(value, dict):
        return {key: resolve_placeholders(item, previous_response) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve_placeholders(item, previous_response) for item in value]
    if not isinstance(value, str):
        return value
    if value == "${last._scroll_id}":
        return ((previous_response.get("body") or {}).get("_scroll_id"))
    if value == "${last.id}":
        body = previous_response.get("body") or {}
        return body.get("id") or body.get("pit_id")
    return value


def http_json(
    base_url: str,
    method: str,
    path: str,
    body: Any,
    timeout: float,
    raw: bool = False,
    accept: str | None = None,
) -> dict[str, Any]:
    data: bytes | None
    headers = {"Accept": accept or "application/json"}
    if raw:
        data = body.encode("utf-8")
        headers["Content-Type"] = "application/x-ndjson"
    elif body is None:
        data = None
    else:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(base_url + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return decode_response(response.status, response.read())
    except urllib.error.HTTPError as error:
        return decode_response(error.code, error.read())
    except urllib.error.URLError as error:
        return {"status": 0, "body": {}, "error": str(error)}


def decode_response(status: int, payload: bytes) -> dict[str, Any]:
    if not payload:
        return {"status": status, "body": {}}
    try:
        body = json.loads(payload.decode("utf-8"))
    except json.JSONDecodeError:
        body = {"_raw": payload.decode("utf-8", errors="replace")}
    return {"status": status, "body": body}


def bulk_body(index: str, documents: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for doc in documents:
        lines.append(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, sort_keys=True))
        lines.append(json.dumps(doc["_source"], sort_keys=True))
    return "\n".join(lines) + "\n"


def extract(kind: str, response: dict[str, Any]) -> Any:
    body = response.get("body") or {}
    if kind == "status_only":
        return {"status": response["status"]}
    if kind == "root_info":
        return {
            "status": response["status"],
            "tagline": body.get("tagline"),
            "version_number_present": bool((body.get("version") or {}).get("number")),
        }
    if kind == "cluster_health":
        return {
            "status": response["status"],
            "health": body.get("status"),
            "timed_out": body.get("timed_out"),
        }
    if kind == "get_index":
        index_body = next(iter(body.values()), {}) if isinstance(body, dict) and body else {}
        mappings = index_body.get("mappings", {})
        properties = mappings.get("properties", {})
        return {
            "status": response["status"],
            "fields": sorted(properties.keys()),
        }
    if kind == "index_metadata":
        index_body = next(iter(body.values()), {}) if isinstance(body, dict) and body else {}
        settings = ((index_body.get("settings") or {}).get("index") or {})
        aliases = index_body.get("aliases") or {}
        mappings = index_body.get("mappings") or {}
        properties = mappings.get("properties") or {}
        return {
            "status": response["status"],
            "aliases": sorted(aliases.keys()),
            "fields": sorted(properties.keys()),
            "number_of_shards": str(settings.get("number_of_shards")),
            "number_of_replicas": str(settings.get("number_of_replicas")),
        }
    if kind == "alias_metadata":
        alias_pairs: list[str] = []
        for index, index_body in (sorted(body.items()) if isinstance(body, dict) else []):
            aliases = (index_body.get("aliases") or {}) if isinstance(index_body, dict) else {}
            for alias in sorted(aliases.keys()):
                alias_pairs.append(f"{index}:{alias}")
        return {
            "status": response["status"],
            "aliases": alias_pairs,
        }
    if kind == "get_document":
        return {
            "status": response["status"],
            "found": body.get("found"),
            "_id": body.get("_id"),
            "_source": body.get("_source"),
        }
    if kind == "search_hits":
        hits = ((body.get("hits") or {}).get("hits") or [])
        total = (body.get("hits") or {}).get("total")
        if isinstance(total, dict):
            total_value = total.get("value")
        else:
            total_value = total
        return {
            "status": response["status"],
            "total": total_value,
            "ids": [hit.get("_id") for hit in hits],
            "sources": [hit.get("_source") for hit in hits],
        }
    if kind == "search_summary":
        hits = ((body.get("hits") or {}).get("hits") or [])
        total = (body.get("hits") or {}).get("total")
        shards = body.get("_shards") or {}
        if isinstance(total, dict):
            total_value = total.get("value")
            total_relation = total.get("relation")
        else:
            total_value = total
            total_relation = None
        return {
            "status": response["status"],
            "total": total_value,
            "relation": total_relation,
            "ids": [hit.get("_id") for hit in hits],
            "timed_out": body.get("timed_out"),
            "terminated_early": body.get("terminated_early"),
            "shards": {
                "total": shards.get("total"),
                "successful": shards.get("successful"),
                "skipped": shards.get("skipped"),
                "failed": shards.get("failed"),
            },
        }
    if kind == "search_explain":
        hits = ((body.get("hits") or {}).get("hits") or [])
        return {
            "status": response["status"],
            "ids": [hit.get("_id") for hit in hits if isinstance(hit, dict)],
            "explanation_present": all(
                isinstance(hit, dict) and isinstance(hit.get("_explanation"), dict)
                for hit in hits
            ),
        }
    if kind == "search_profile":
        profile = body.get("profile") or {}
        shards = profile.get("shards") if isinstance(profile, dict) else None
        first_shard = shards[0] if isinstance(shards, list) and shards else {}
        first_search = (
            (first_shard.get("searches") or [])[0]
            if isinstance(first_shard, dict) and first_shard.get("searches")
            else {}
        )
        query_nodes = first_search.get("query") if isinstance(first_search, dict) else None
        collector_nodes = first_search.get("collector") if isinstance(first_search, dict) else None
        return {
            "status": response["status"],
            "profile_present": isinstance(profile, dict) and bool(profile),
            "shards_present": isinstance(shards, list) and bool(shards),
            "query_nodes_present": isinstance(query_nodes, list) and bool(query_nodes),
            "collector_nodes_present": isinstance(collector_nodes, list) and bool(collector_nodes),
        }
    if kind == "search_fields":
        hits = ((body.get("hits") or {}).get("hits") or [])
        total = (body.get("hits") or {}).get("total")
        if isinstance(total, dict):
            total_value = total.get("value")
        else:
            total_value = total
        return {
            "status": response["status"],
            "total": total_value,
            "ids": [hit.get("_id") for hit in hits if isinstance(hit, dict)],
            "fields": {
                hit.get("_id"): hit.get("fields")
                for hit in hits
                if isinstance(hit, dict) and hit.get("_id") is not None
            },
        }
    if kind == "highlight_hits":
        hits = ((body.get("hits") or {}).get("hits") or [])
        total = (body.get("hits") or {}).get("total")
        if isinstance(total, dict):
            total_value = total.get("value")
        else:
            total_value = total
        return {
            "status": response["status"],
            "total": total_value,
            "ids": [hit.get("_id") for hit in hits],
            "highlights": {
                hit.get("_id"): hit.get("highlight")
                for hit in hits
                if isinstance(hit, dict) and hit.get("_id") is not None
            },
        }
    if kind == "suggest_response":
        suggest = body.get("suggest") or {}
        normalized: dict[str, Any] = {}
        if isinstance(suggest, dict):
            for name, entries in sorted(suggest.items()):
                if not isinstance(entries, list):
                    continue
                normalized[name] = [
                    {
                        "text": entry.get("text"),
                        "options": [
                            option.get("text")
                            for option in (entry.get("options") or [])
                            if isinstance(option, dict)
                        ],
                    }
                    for entry in entries
                    if isinstance(entry, dict)
                ]
        return {
            "status": response["status"],
            "suggest": normalized,
        }
    if kind == "scroll_hits":
        hits = ((body.get("hits") or {}).get("hits") or [])
        return {
            "status": response["status"],
            "scroll_id_present": bool(body.get("_scroll_id")),
            "ids": [hit.get("_id") for hit in hits if isinstance(hit, dict)],
        }
    if kind == "scroll_clear":
        return {
            "status": response["status"],
            "succeeded": body.get("succeeded"),
            "num_freed": body.get("num_freed"),
        }
    if kind == "pit_open":
        return {
            "status": response["status"],
            "id_present": bool(body.get("id") or body.get("pit_id")),
        }
    if kind == "pit_clear":
        pits = body.get("pits")
        if isinstance(pits, list):
            freed_count = sum(
                1
                for item in pits
                if isinstance(item, dict) and item.get("successful") is True
            )
        else:
            freed_count = body.get("num_freed")
        return {
            "status": response["status"],
            "freed_count": freed_count,
        }
    if kind == "terms_aggregation":
        aggs = body.get("aggregations") or {}
        first_agg = next(iter(aggs.values()), {})
        buckets = first_agg.get("buckets") or []
        return {
            "status": response["status"],
            "buckets": [{"key": bucket.get("key"), "doc_count": bucket.get("doc_count")} for bucket in buckets],
        }
    if kind == "aggregations":
        return {
            "status": response["status"],
            "aggregations": normalize_aggregations(body.get("aggregations") or {}),
        }
    if kind == "error_response":
        error = body.get("error") or {}
        if isinstance(error, dict):
            error_type = error.get("type")
            reason = error.get("reason")
        else:
            error_type = None
            reason = error
        return {
            "status": response["status"],
            "error_type": error_type,
            "reason_present": bool(reason),
        }
    if kind == "knn_warmup":
        return {
            "status": response["status"],
            "index": body.get("index"),
            "warmed": body.get("warmed"),
            "vector_segment_count": body.get("vector_segment_count"),
            "native_memory_bytes": body.get("native_memory_bytes"),
            "model_cache_bytes": body.get("model_cache_bytes"),
            "quantization_cache_bytes": body.get("quantization_cache_bytes"),
        }
    if kind == "knn_clear_cache":
        return {
            "status": response["status"],
            "index": body.get("index"),
            "cleared_entries": body.get("cleared_entries"),
            "released_native_memory_bytes": body.get("released_native_memory_bytes"),
            "released_model_cache_bytes": body.get("released_model_cache_bytes"),
            "released_quantization_cache_bytes": body.get("released_quantization_cache_bytes"),
        }
    if kind == "knn_stats":
        local = ((body.get("nodes") or {}).get("local") or {})
        return {
            "status": response["status"],
            "graph_count": local.get("graph_count"),
            "warmed_index_count": local.get("warmed_index_count"),
            "cache_entry_count": local.get("cache_entry_count"),
            "native_memory_used_bytes": local.get("native_memory_used_bytes"),
            "model_cache_used_bytes": local.get("model_cache_used_bytes"),
            "quantization_cache_used_bytes": local.get("quantization_cache_used_bytes"),
            "clear_cache_requests": local.get("clear_cache_requests"),
            "circuit_breaker_triggered": local.get("circuit_breaker_triggered"),
            "operational_controls_present": isinstance(local.get("operational_controls"), dict),
        }
    if kind == "cat_indices":
        rows = body if isinstance(body, list) else []
        indices = {row.get("index") for row in rows if isinstance(row, dict)}
        columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        return {
            "status": response["status"],
            "fixture_indices_present": sorted(COMPAT_INDICES & indices),
            "required_columns_present": sorted(CAT_INDEX_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_indices_text":
        raw = body.get("_raw") if isinstance(body, dict) else None
        lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
        header = lines[0].split() if lines else []
        indices = []
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 3:
                indices.append(parts[2])
        return {
            "status": response["status"],
            "fixture_indices_present": sorted(COMPAT_INDICES & set(indices)),
            "required_columns_present": sorted(CAT_INDEX_REQUIRED_COLUMNS & set(header)),
        }
    if kind == "cat_count":
        if isinstance(body, list):
            row = body[0] if body and isinstance(body[0], dict) else {}
            count = row.get("count")
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            data_line = lines[-1] if lines else ""
            parts = data_line.split()
            count = parts[-1] if parts else None
        return {
            "status": response["status"],
            "count": count,
        }
    if kind == "cat_pending_tasks":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_PENDING_TASKS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_aliases":
        if isinstance(body, list):
            rows = body
            aliases = {row.get("alias") for row in rows if isinstance(row, dict)}
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            header = lines[0].split() if lines else []
            aliases = set()
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    aliases.add(parts[0])
            columns = set(header)
        return {
            "status": response["status"],
            "fixture_aliases_present": sorted({"logs-compat-read"} & aliases),
            "required_columns_present": sorted(CAT_ALIAS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_allocation":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_ALLOCATION_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_fielddata":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_FIELDDATA_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_health":
        if isinstance(body, list):
            row = body[0] if body and isinstance(body[0], dict) else {}
            columns = set(row.keys())
            cluster = row.get("cluster")
            health_status = row.get("status")
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            header = lines[0].split() if lines else []
            data = lines[-1].split() if len(lines) > 1 else []
            columns = set(header)
            cluster = data[2] if len(data) > 2 else None
            health_status = data[3] if len(data) > 3 else None
        return {
            "status": response["status"],
            "cluster_present": bool(cluster),
            "health_status": health_status,
            "required_columns_present": sorted(CAT_HEALTH_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_nodes":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            node_names = {row.get("name") for row in rows if isinstance(row, dict)}
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            header = lines[0].split() if lines else []
            columns = set(header)
            node_names = set()
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    node_names.add(parts[-1])
        return {
            "status": response["status"],
            "node_count": len(node_names),
            "required_columns_present": sorted(CAT_NODES_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_nodeattrs":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            node_names = {row.get("node") for row in rows if isinstance(row, dict)}
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            header = lines[0].split() if lines else []
            columns = set(header)
            node_names = set()
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    node_names.add(parts[0])
        return {
            "status": response["status"],
            "node_count": len(node_names),
            "required_columns_present": sorted(CAT_NODEATTRS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_shards":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            row_count = len(rows)
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            row_count = max(len(lines) - 1, 0)
        return {
            "status": response["status"],
            "row_count": row_count,
            "required_columns_present": sorted(CAT_SHARDS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_segments":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            row_count = len(rows)
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            row_count = max(len(lines) - 1, 0)
        return {
            "status": response["status"],
            "row_count": row_count,
            "required_columns_present": sorted(CAT_SEGMENTS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_pit_segments":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            row_count = len(rows)
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            row_count = max(len(lines) - 1, 0)
        return {
            "status": response["status"],
            "row_count": row_count,
            "required_columns_present": sorted(CAT_PIT_SEGMENTS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_recovery":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_RECOVERY_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_repositories":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_REPOSITORIES_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_snapshots":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            row_count = len(rows)
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            row_count = max(len(lines) - 1, 0)
        return {
            "status": response["status"],
            "row_count": row_count,
            "required_columns_present": sorted(CAT_SNAPSHOTS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_tasks":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_TASKS_REQUIRED_COLUMNS & columns),
        }
    if kind == "cat_templates":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            template_names = {row.get("name") for row in rows if isinstance(row, dict)}
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            template_names = set()
            for line in lines[1:]:
                parts = line.split()
                if parts:
                    template_names.add(parts[0])
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_TEMPLATES_REQUIRED_COLUMNS & columns),
            "fixture_templates_present": sorted(
                {"logs-template"} & {name for name in template_names if isinstance(name, str)}
            ),
        }
    if kind == "cat_thread_pool":
        if isinstance(body, list):
            rows = body
            columns = set(rows[0].keys()) if rows and isinstance(rows[0], dict) else set()
            pool_names = {row.get("name") for row in rows if isinstance(row, dict)}
        else:
            raw = body.get("_raw") if isinstance(body, dict) else None
            lines = [line.strip() for line in (raw or "").splitlines() if line.strip()]
            columns = set(lines[0].split()) if lines else set()
            pool_names = set()
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    pool_names.add(parts[1])
        return {
            "status": response["status"],
            "required_columns_present": sorted(CAT_THREAD_POOL_REQUIRED_COLUMNS & columns),
            "fixture_thread_pools_present": sorted(
                {"search"} & {name for name in pool_names if isinstance(name, str)}
            ),
        }
    if kind == "decommission_status":
        entries = []
        if isinstance(body, dict):
            entries = sorted(
                (str(key), str(value))
                for key, value in body.items()
                if not str(key).startswith("_")
            )
        return {
            "status": response["status"],
            "entries": entries,
        }
    if kind == "weighted_routing":
        weights = body.get("weights") if isinstance(body, dict) else None
        return {
            "status": response["status"],
            "weight_keys": sorted(weights.keys()) if isinstance(weights, dict) else [],
            "weights": weights if isinstance(weights, dict) else {},
            "version_present": isinstance(body, dict) and "version" in body,
            "discovered_cluster_manager_present": isinstance(body, dict)
            and "discovered_cluster_manager" in body,
        }
    if kind == "hot_threads_text":
        raw = body.get("_raw") if isinstance(body, dict) else ""
        raw = raw or ""
        return {
            "status": response["status"],
            "hot_threads_marker_present": "Hot threads at" in raw,
        }
    if kind == "cat_help":
        raw = body.get("_raw") if isinstance(body, dict) else ""
        raw = raw or ""
        return {
            "status": response["status"],
            "help_banner_present": "=^.^=" in raw,
            "required_entries_present": sorted(
                entry
                for entry in ["/_cat/aliases", "/_cat/health", "/_cat/nodes", "/_cat/shards"]
                if entry in raw
            ),
        }
    if kind == "dangling_indices":
        dangling_indices = body.get("dangling_indices") if isinstance(body, dict) else None
        nodes = body.get("_nodes") if isinstance(body, dict) else None
        return {
            "status": response["status"],
            "cluster_name_present": bool(body.get("cluster_name")) if isinstance(body, dict) else False,
            "dangling_indices_count": len(dangling_indices) if isinstance(dangling_indices, list) else None,
            "nodes_total": nodes.get("total") if isinstance(nodes, dict) else None,
            "nodes_successful": nodes.get("successful") if isinstance(nodes, dict) else None,
            "nodes_failed": nodes.get("failed") if isinstance(nodes, dict) else None,
        }
    if kind == "remote_info":
        return {
            "status": response["status"],
            "cluster_keys": sorted(body.keys()) if isinstance(body, dict) else None,
        }
    if kind == "remote_store_metadata":
        shards = body.get("_shards") if isinstance(body, dict) else None
        failures = shards.get("failures") if isinstance(shards, dict) else None
        first_failure = failures[0] if isinstance(failures, list) and failures else {}
        reason = first_failure.get("reason") if isinstance(first_failure, dict) else {}
        return {
            "status": response["status"],
            "shards_total": shards.get("total") if isinstance(shards, dict) else None,
            "shards_successful": shards.get("successful") if isinstance(shards, dict) else None,
            "shards_failed": shards.get("failed") if isinstance(shards, dict) else None,
            "failure_reason_type": reason.get("type") if isinstance(reason, dict) else None,
            "failure_reason": reason.get("reason") if isinstance(reason, dict) else None,
            "indices_keys": sorted(body.get("indices", {}).keys()) if isinstance(body, dict) and isinstance(body.get("indices"), dict) else None,
        }
    if kind == "remote_store_missing_index":
        error = body.get("error") if isinstance(body, dict) else None
        return {
            "status": response["status"],
            "error_type": error.get("type") if isinstance(error, dict) else None,
            "error_index": error.get("index") if isinstance(error, dict) else None,
        }
    if kind == "remote_store_stats":
        shards = body.get("_shards") if isinstance(body, dict) else None
        return {
            "status": response["status"],
            "shards_total": shards.get("total") if isinstance(shards, dict) else None,
            "shards_successful": shards.get("successful") if isinstance(shards, dict) else None,
            "shards_failed": shards.get("failed") if isinstance(shards, dict) else None,
            "indices_keys": sorted(body.get("indices", {}).keys()) if isinstance(body, dict) and isinstance(body.get("indices"), dict) else None,
        }
    if kind == "cluster_stats_indices_only":
        indices = body.get("indices") or {}
        return {
            "status": response["status"],
            "cluster_name_present": bool(body.get("cluster_name")),
            "index_count_present": "count" in indices,
        }
    if kind == "cluster_stats_index_metric":
        indices = body.get("indices") or {}
        docs = indices.get("docs") or {}
        return {
            "status": response["status"],
            "cluster_name_present": bool(body.get("cluster_name")),
            "docs_count_present": "count" in docs,
        }
    if kind == "node_stats":
        nodes = body.get("nodes") or {}
        first = next(iter(nodes.values()), {}) if isinstance(nodes, dict) and nodes else {}
        return {
            "status": response["status"],
            "nodes_present": bool(nodes) if isinstance(nodes, dict) else False,
            "indices_count_present": "count" in (first.get("indices") or {}),
        }
    if kind == "node_usage":
        nodes = body.get("nodes") or {}
        first = next(iter(nodes.values()), {}) if isinstance(nodes, dict) and nodes else {}
        return {
            "status": response["status"],
            "nodes_present": bool(nodes) if isinstance(nodes, dict) else False,
            "rest_actions_present": isinstance(first.get("rest_actions"), dict),
        }
    if kind == "node_info":
        nodes = body.get("nodes") or {}
        first = next(iter(nodes.values()), {}) if isinstance(nodes, dict) and nodes else {}
        return {
            "status": response["status"],
            "nodes_present": bool(nodes) if isinstance(nodes, dict) else False,
            "roles_present": isinstance(first.get("roles"), list),
            "http_present": isinstance(first.get("http"), dict),
        }
    if kind == "search_shards":
        indices = body.get("indices") or {}
        shard_groups = body.get("shards") or []
        first_group = shard_groups[0] if isinstance(shard_groups, list) and shard_groups else []
        first_shard = first_group[0] if isinstance(first_group, list) and first_group else {}
        fixture_indices = {"logs-root-cat-000001", "metrics-root-cat-000001"}
        fixture_shard_groups = [
            group
            for group in shard_groups
            if isinstance(group, list)
            and group
            and isinstance(group[0], dict)
            and group[0].get("index") in fixture_indices
        ] if isinstance(shard_groups, list) else []
        return {
            "status": response["status"],
            "fixture_indices_present": sorted(fixture_indices & set(indices.keys()))
            if isinstance(indices, dict)
            else [],
            "nodes_present": isinstance(body.get("nodes"), dict) and bool(body.get("nodes")),
            "fixture_shard_group_count": len(fixture_shard_groups),
            "first_state": first_shard.get("state"),
            "first_primary": first_shard.get("primary"),
            "first_search_only": first_shard.get("searchOnly"),
        }
    if kind == "script_context":
        contexts = body.get("contexts") or []
        names = {
            item.get("name")
            for item in contexts
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        } if isinstance(contexts, list) else set()
        return {
            "status": response["status"],
            "required_contexts_present": sorted({"filter", "score", "template", "update"} & names),
            "contexts_nonempty": bool(contexts) if isinstance(contexts, list) else False,
        }
    if kind == "script_language":
        language_contexts = body.get("language_contexts") or []
        languages = {
            item.get("language")
            for item in language_contexts
            if isinstance(item, dict) and isinstance(item.get("language"), str)
        } if isinstance(language_contexts, list) else set()
        return {
            "status": response["status"],
            "types_allowed": sorted(set(body.get("types_allowed") or []) & {"inline", "stored"})
            if isinstance(body.get("types_allowed"), list)
            else [],
            "required_languages_present": sorted({"mustache", "painless"} & languages),
        }
    if kind == "stored_script_get":
        script = body.get("script") or {}
        return {
            "status": response["status"],
            "found": body.get("found"),
            "_id": body.get("_id"),
            "lang": script.get("lang") if isinstance(script, dict) else None,
            "source": script.get("source") if isinstance(script, dict) else None,
        }
    if kind == "acknowledged":
        return {
            "status": response["status"],
            "acknowledged": body.get("acknowledged"),
        }
    if kind == "cluster_stats":
        return {
            "status": response["status"],
            "cluster_name_present": bool(body.get("cluster_name")),
            "index_count_present": "count" in (body.get("indices") or {}),
            "node_total_present": "total" in (((body.get("nodes") or {}).get("count") or {})),
        }
    if kind == "index_stats":
        indices = body.get("indices") or {}
        return {
            "status": response["status"],
            "fixture_indices_present": sorted(COMPAT_INDICES & set(indices.keys())) if isinstance(indices, dict) else [],
            "all_total_docs_present": "docs" in (((body.get("_all") or {}).get("total") or {})),
        }
    if kind == "knn_stats_shape":
        nodes = body.get("nodes") or {}
        return {
            "status": response["status"],
            "nodes_present": isinstance(nodes, dict) and bool(nodes),
        }
    if kind == "knn_stats_accounting":
        node = first_node(body)
        return {
            "status": response["status"],
            "graph_count": node.get("graph_count"),
            "warmed_index_count": node.get("warmed_index_count"),
            "cache_entry_count": node.get("cache_entry_count"),
            "native_memory_used_bytes": node.get("native_memory_used_bytes"),
            "model_cache_used_bytes": node.get("model_cache_used_bytes"),
            "quantization_cache_used_bytes": node.get("quantization_cache_used_bytes"),
            "operational_controls_present": isinstance(node.get("operational_controls"), dict),
        }
    if kind == "knn_warmup_response":
        return {
            "status": response["status"],
            "index": body.get("index"),
            "warmed": body.get("warmed"),
            "vector_segment_count": body.get("vector_segment_count"),
            "native_memory_bytes": body.get("native_memory_bytes"),
            "model_cache_bytes": body.get("model_cache_bytes"),
            "quantization_cache_bytes": body.get("quantization_cache_bytes"),
        }
    if kind == "knn_clear_cache_response":
        return {
            "status": response["status"],
            "index": body.get("index"),
            "cleared_entries": body.get("cleared_entries"),
            "released_native_memory_bytes": body.get("released_native_memory_bytes"),
            "released_model_cache_bytes": body.get("released_model_cache_bytes"),
            "released_quantization_cache_bytes": body.get("released_quantization_cache_bytes"),
        }
    if kind == "tasks":
        return {
            "status": response["status"],
            "tasks_present": isinstance(body.get("tasks"), dict),
            "nodes_present": isinstance(body.get("nodes"), dict),
        }
    if kind == "allocation_explain":
        decisions = body.get("node_allocation_decisions")
        return {
            "status": response["status"],
            "index_present": bool(body.get("index")),
            "current_state": body.get("current_state"),
            "node_decisions_present": isinstance(decisions, list),
        }
    return {"status": response["status"], "body": body}


def first_node(body: dict[str, Any]) -> dict[str, Any]:
    nodes = body.get("nodes") or {}
    if not isinstance(nodes, dict) or not nodes:
        return {}
    first = next(iter(nodes.values()), {})
    return first if isinstance(first, dict) else {}


def normalize_aggregations(aggregations: dict[str, Any]) -> dict[str, Any]:
    return {
        name: normalize_aggregation_value(value)
        for name, value in sorted(aggregations.items())
        if isinstance(value, dict)
    }


def normalize_aggregation_value(value: dict[str, Any]) -> Any:
    if "buckets" in value:
        buckets = value.get("buckets")
        if isinstance(buckets, list):
            return {
                "buckets": sorted(
                    (
                        {
                            "key": bucket.get("key_as_string", bucket.get("key")),
                            "doc_count": bucket.get("doc_count"),
                        }
                        for bucket in buckets
                        if isinstance(bucket, dict)
                    ),
                    key=lambda bucket: json.dumps(bucket.get("key"), sort_keys=True),
                )
            }
        if isinstance(buckets, dict):
            return {
                "buckets": {
                    key: {"doc_count": bucket.get("doc_count")}
                    for key, bucket in sorted(buckets.items())
                    if isinstance(bucket, dict)
                }
            }
    if "hits" in value:
        hits = value.get("hits") or {}
        hit_rows = hits.get("hits") or []
        return {
            "total": (hits.get("total") or {}).get("value"),
            "ids": sorted(hit.get("_id") for hit in hit_rows if isinstance(hit, dict)),
        }
    if "bounds" in value:
        return {"bounds": normalize_geo_bounds(value.get("bounds"))}
    if "top_left" in value or "bottom_right" in value:
        return normalize_geo_bounds(value)
    if "_plugin" in value:
        return {
            "_plugin": value.get("_plugin"),
            "_type": value.get("_type"),
            "params": value.get("params"),
            "value": value.get("value"),
        }
    if "doc_count" in value:
        return {"doc_count": value.get("doc_count")}
    if "value" in value:
        return {"value": value.get("value")}
    return value


def normalize_geo_bounds(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    return {
        corner: normalize_geo_point(value.get(corner))
        for corner in ("top_left", "bottom_right")
        if corner in value
    }


def normalize_geo_point(value: Any) -> Any:
    if not isinstance(value, dict):
        return value
    normalized: dict[str, Any] = {}
    for coordinate in ("lat", "lon"):
        raw = value.get(coordinate)
        normalized[coordinate] = round(raw, 5) if isinstance(raw, (int, float)) else raw
    return normalized


def status_for(response: dict[str, Any]) -> str:
    return "passed" if 200 <= response["status"] < 300 else "failed"


def missing_knn_plugin_response(response: dict[str, Any]) -> bool:
    body = response.get("body") or {}
    error = body.get("error") or {}
    reason = error.get("reason") if isinstance(error, dict) else None
    return (
        response.get("status") == 400
        and isinstance(reason, str)
        and "unknown setting [index.knn]" in reason
    )


def missing_runtime_mappings_support(response: dict[str, Any]) -> bool:
    body = response.get("body") or {}
    if response.get("status") != 400:
        return False
    error = body.get("error") or {}
    if not isinstance(error, dict):
        return False
    reason = error.get("reason") or ""
    return isinstance(reason, str) and "runtime_mappings" in reason


def missing_knn_query_response(response: dict[str, Any]) -> bool:
    body = response.get("body") or {}
    error = body.get("error") or {}
    if not isinstance(error, dict) or error.get("type") != "parsing_exception":
        return False
    reason = str(error.get("reason") or "")
    caused_by = error.get("caused_by") or {}
    caused_reason = str(caused_by.get("reason") or "") if isinstance(caused_by, dict) else ""
    return "unknown query [knn]" in reason or "unknown field [knn]" in caused_reason


def step_result(
    target: str,
    name: str,
    status: str,
    response: dict[str, Any],
    skip_scope: str | None = None,
    skipped_reason: str | None = None,
) -> dict[str, Any]:
    result = {
        "target": target,
        "name": name,
        "status": status,
        "http_status": response["status"],
        "error": response.get("error") or (response.get("body") or {}).get("error"),
        "raw_response": raw_response(response),
        "normalized_response": normalized_response(response),
    }
    if skip_scope is not None:
        result["skip_scope"] = skip_scope
    if skipped_reason is not None:
        result["skipped_reason"] = skipped_reason
    return result


def raw_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": response["status"],
        "body": response.get("body") or {},
        "error": response.get("error"),
    }


def normalized_response(response: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": response["status"],
        "body": normalize_value(response.get("body") or {}),
        "error": normalize_value(response.get("error")),
    }


def normalize_value(value: Any) -> Any:
    if isinstance(value, dict):
        normalized: dict[str, Any] = {}
        for key, child in value.items():
            if key in VOLATILE_RESPONSE_KEYS:
                continue
            if key == "_shards" and isinstance(child, dict):
                normalized[key] = {
                    child_key: normalize_value(child_value)
                    for child_key, child_value in child.items()
                    if child_key != "failures"
                }
                continue
            normalized[key] = normalize_value(child)
        return normalized
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    return value


if __name__ == "__main__":
    raise SystemExit(main())
