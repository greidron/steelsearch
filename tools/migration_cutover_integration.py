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
    parser.add_argument(
        "--checkpoint",
        default=os.environ.get(
            "MIGRATION_CUTOVER_CHECKPOINT",
            str(DEFAULT_OUTPUT.with_suffix(".checkpoint.json")),
        ),
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


def load_checkpoint(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "completed_operations": [],
            "operation_records": {},
        }
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        "completed_operations": data.get("completed_operations", []),
        "operation_records": data.get("operation_records", {}),
    }


def save_checkpoint(path: Path, checkpoint: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def extract_path(value: Any, path: str) -> Any:
    current = value
    for token in path.split("."):
        if isinstance(current, list):
            if not token.isdigit():
                return None
            index = int(token)
            if index >= len(current):
                return None
            current = current[index]
            continue
        if not isinstance(current, dict):
            return None
        if token not in current:
            return None
        current = current[token]
    return current


def search_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
    }


def path_summary(response: dict[str, Any], paths: list[str]) -> dict[str, Any]:
    body = response.get("body") or {}
    summary: dict[str, Any] = {"status": response.get("status")}
    for path in paths:
        summary[path] = extract_path(body, path)
    return summary


def template_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    templates = body.get("component_templates") or body.get("index_templates") or []
    summary: list[dict[str, Any]] = []
    for entry in templates:
        if "component_template" in entry:
            template = entry.get("component_template") or {}
            mappings = (((template.get("template") or {}).get("mappings") or {}).get("properties") or {})
            summary.append(
                {
                    "name": entry.get("name"),
                    "kind": "component_template",
                    "property_types": {
                        field: (spec or {}).get("type")
                        for field, spec in sorted(mappings.items())
                    },
                    "meta_keys": sorted(((template.get("_meta") or {}).keys())),
                }
            )
        elif "index_template" in entry:
            template = entry.get("index_template") or {}
            mappings = (((template.get("template") or {}).get("mappings") or {}).get("properties") or {})
            summary.append(
                {
                    "name": entry.get("name"),
                    "kind": "index_template",
                    "index_patterns": template.get("index_patterns") or [],
                    "composed_of": template.get("composed_of") or [],
                    "has_data_stream": "data_stream" in template,
                    "property_types": {
                        field: (spec or {}).get("type")
                        for field, spec in sorted(mappings.items())
                    },
                }
            )
    return {"status": response.get("status"), "templates": summary}


def index_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    indices: list[dict[str, Any]] = []
    for index_name in sorted(body.keys()):
        index_body = body.get(index_name) or {}
        settings = (((index_body.get("settings") or {}).get("index")) or {})
        mappings = (((index_body.get("mappings") or {}).get("properties")) or {})
        aliases = (index_body.get("aliases") or {})
        indices.append(
            {
                "name": index_name,
                "number_of_shards": settings.get("number_of_shards"),
                "number_of_replicas": settings.get("number_of_replicas"),
                "refresh_interval": settings.get("refresh_interval"),
                "property_types": {
                    field: (spec or {}).get("type")
                    for field, spec in sorted(mappings.items())
                },
                "alias_names": sorted(aliases.keys()),
            }
        )
    return {"status": response.get("status"), "indices": indices}


def alias_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    aliases: list[dict[str, Any]] = []
    for index_name in sorted(body.keys()):
        alias_map = ((body.get(index_name) or {}).get("aliases") or {})
        for alias_name in sorted(alias_map.keys()):
            alias_body = alias_map.get(alias_name) or {}
            aliases.append(
                {
                    "index": index_name,
                    "alias": alias_name,
                    "is_write_index": alias_body.get("is_write_index"),
                    "routing": alias_body.get("routing"),
                    "index_routing": alias_body.get("index_routing"),
                    "search_routing": alias_body.get("search_routing"),
                    "has_filter": "filter" in alias_body,
                }
            )
    return {"status": response.get("status"), "aliases": aliases}


def data_stream_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    data_streams = body.get("data_streams") or []
    summary: list[dict[str, Any]] = []
    for entry in data_streams:
        summary.append(
            {
                "name": entry.get("name"),
                "generation": entry.get("generation"),
                "template": entry.get("template"),
                "index_names": [
                    (item or {}).get("index_name") for item in (entry.get("indices") or [])
                ],
            }
        )
    return {"status": response.get("status"), "data_streams": summary}


def iter_mapping_properties(
    properties: dict[str, Any],
    prefix: str = "",
) -> list[tuple[str, dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any]]] = []
    for field_name, field_spec in sorted(properties.items()):
        if not isinstance(field_spec, dict):
            continue
        qualified_name = f"{prefix}.{field_name}" if prefix else field_name
        entries.append((qualified_name, field_spec))
        nested_properties = ((field_spec.get("properties") or {}) if isinstance(field_spec, dict) else {})
        if isinstance(nested_properties, dict) and nested_properties:
            entries.extend(iter_mapping_properties(nested_properties, qualified_name))
    return entries


def unsupported_feature_preflight_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    blockers: list[dict[str, Any]] = []
    degraded: list[dict[str, Any]] = []

    for index_name in sorted(body.keys()):
        index_body = body.get(index_name) or {}
        properties = (((index_body.get("mappings") or {}).get("properties")) or {})
        if not isinstance(properties, dict):
            continue
        for field_name, field_spec in iter_mapping_properties(properties):
            if field_spec.get("type") != "knn_vector":
                continue
            method = field_spec.get("method") or {}
            engine = method.get("engine")
            mode = field_spec.get("mode")
            space_type = method.get("space_type")
            reasons: list[str] = []
            if engine not in (None, "lucene"):
                reasons.append(f"unsupported knn engine [{engine}]")
            if mode not in (None, "in_memory"):
                reasons.append(f"unsupported knn mode [{mode}]")
            if space_type not in (None, "l2", "cosinesimil", "innerproduct"):
                reasons.append(f"unsupported knn space_type [{space_type}]")
            if reasons:
                blockers.append(
                    {
                        "classification": "migrate-blocking",
                        "family": "Search DSL",
                        "feature": "unsupported vector/k-NN options outside current fail-closed surface",
                        "index": index_name,
                        "field": field_name,
                        "reasons": reasons,
                    }
                )
                continue
            degraded.append(
                {
                    "classification": "degraded-but-allowed",
                    "family": "Mapping feature",
                    "feature": "bounded executable k-NN vector subset",
                    "index": index_name,
                    "field": field_name,
                }
            )

    return {
        "status": response.get("status"),
        "blockers": blockers,
        "degraded": degraded,
    }


def vector_payload_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    source = body.get("_source") or {}
    embedding = source.get("embedding")
    values = embedding if isinstance(embedding, list) else []
    return {
        "status": response.get("status"),
        "_id": body.get("_id"),
        "service": source.get("service"),
        "tenant": source.get("tenant"),
        "vector_length": len(values),
        "vector_values": values,
    }


def vector_ranking_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "top_ids": [hit.get("_id") for hit in hits],
    }


def scroll_hits_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    hits = ((body.get("hits") or {}).get("hits") or [])
    total = ((body.get("hits") or {}).get("total") or {}).get("value")
    return {
        "status": response.get("status"),
        "total": total,
        "ids": [hit.get("_id") for hit in hits],
        "scroll_id_present": bool(body.get("_scroll_id")),
    }


def scroll_clear_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    return {
        "status": response.get("status"),
        "succeeded": body.get("succeeded"),
        "num_freed": body.get("num_freed"),
    }


def pit_open_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    return {
        "status": response.get("status"),
        "id_present": bool(body.get("id") or body.get("pit_id")),
    }


def pit_clear_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    pits = body.get("pits")
    return {
        "status": response.get("status"),
        "succeeded": body.get("succeeded"),
        "pit_ids": [
            (item or {}).get("pit_id")
            for item in pits
            if isinstance(item, dict)
        ]
        if isinstance(pits, list)
        else [],
        "num_freed": body.get("num_freed"),
    }


def resolve_placeholder(value: Any, previous_response: dict[str, Any] | None) -> Any:
    if previous_response is None:
        return value
    body = previous_response.get("body") or {}
    if value == "${last._scroll_id}":
        return body.get("_scroll_id")
    if value in ("${last.id}", "${last.pit_id}"):
        return body.get("id") or body.get("pit_id")
    return value


def materialize_template(value: Any, previous_response: dict[str, Any] | None) -> Any:
    if isinstance(value, dict):
        return {
            key: materialize_template(child, previous_response)
            for key, child in value.items()
        }
    if isinstance(value, list):
        return [materialize_template(child, previous_response) for child in value]
    return resolve_placeholder(value, previous_response)


def template_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    templates = body.get("component_templates") or body.get("index_templates") or []
    summary: list[dict[str, Any]] = []
    for entry in templates:
        if "component_template" in entry:
            template = entry.get("component_template") or {}
            mappings = (((template.get("template") or {}).get("mappings") or {}).get("properties") or {})
            summary.append(
                {
                    "name": entry.get("name"),
                    "kind": "component_template",
                    "property_types": {
                        field: (spec or {}).get("type")
                        for field, spec in sorted(mappings.items())
                    },
                    "meta_keys": sorted(((template.get("_meta") or {}).keys())),
                }
            )
        elif "index_template" in entry:
            template = entry.get("index_template") or {}
            mappings = (((template.get("template") or {}).get("mappings") or {}).get("properties") or {})
            summary.append(
                {
                    "name": entry.get("name"),
                    "kind": "index_template",
                    "index_patterns": template.get("index_patterns") or [],
                    "composed_of": template.get("composed_of") or [],
                    "has_data_stream": "data_stream" in template,
                    "property_types": {
                        field: (spec or {}).get("type")
                        for field, spec in sorted(mappings.items())
                    },
                }
            )
    return {"status": response.get("status"), "templates": summary}


def index_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    indices: list[dict[str, Any]] = []
    for index_name in sorted(body.keys()):
        index_body = body.get(index_name) or {}
        settings = (((index_body.get("settings") or {}).get("index")) or {})
        mappings = (((index_body.get("mappings") or {}).get("properties")) or {})
        aliases = (index_body.get("aliases") or {})
        indices.append(
            {
                "name": index_name,
                "number_of_shards": settings.get("number_of_shards"),
                "number_of_replicas": settings.get("number_of_replicas"),
                "refresh_interval": settings.get("refresh_interval"),
                "property_types": {
                    field: (spec or {}).get("type")
                    for field, spec in sorted(mappings.items())
                },
                "alias_names": sorted(aliases.keys()),
            }
        )
    return {"status": response.get("status"), "indices": indices}


def alias_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    aliases: list[dict[str, Any]] = []
    for index_name in sorted(body.keys()):
        alias_map = ((body.get(index_name) or {}).get("aliases") or {})
        for alias_name in sorted(alias_map.keys()):
            alias_body = alias_map.get(alias_name) or {}
            aliases.append(
                {
                    "index": index_name,
                    "alias": alias_name,
                    "is_write_index": alias_body.get("is_write_index"),
                    "routing": alias_body.get("routing"),
                    "index_routing": alias_body.get("index_routing"),
                    "search_routing": alias_body.get("search_routing"),
                    "has_filter": "filter" in alias_body,
                }
            )
    return {"status": response.get("status"), "aliases": aliases}


def data_stream_metadata_summary(response: dict[str, Any]) -> dict[str, Any]:
    body = response.get("body") or {}
    data_streams = body.get("data_streams") or []
    summary: list[dict[str, Any]] = []
    for entry in data_streams:
        summary.append(
            {
                "name": entry.get("name"),
                "generation": entry.get("generation"),
                "template": entry.get("template"),
                "index_names": [
                    (item or {}).get("index_name") for item in (entry.get("indices") or [])
                ],
            }
        )
    return {"status": response.get("status"), "data_streams": summary}


def summarize_response(check: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    extractor = check.get("extract")
    if extractor == "search_summary":
        return search_summary(response)
    if extractor == "scroll_hits":
        return scroll_hits_summary(response)
    if extractor == "scroll_clear":
        return scroll_clear_summary(response)
    if extractor == "pit_open":
        return pit_open_summary(response)
    if extractor == "pit_clear":
        return pit_clear_summary(response)
    if extractor == "path_summary":
        return path_summary(response, check.get("compare_paths", []))
    if extractor == "template_metadata":
        return template_metadata_summary(response)
    if extractor == "index_metadata":
        return index_metadata_summary(response)
    if extractor == "alias_metadata":
        return alias_metadata_summary(response)
    if extractor == "data_stream_metadata":
        return data_stream_metadata_summary(response)
    if extractor == "unsupported_feature_preflight":
        return unsupported_feature_preflight_summary(response)
    if extractor == "vector_payload":
        return vector_payload_summary(response)
    if extractor == "vector_ranking":
        return vector_ranking_summary(response)
    if check.get("compare_paths"):
        return path_summary(response, check["compare_paths"])
    return {
        "status": response.get("status"),
        "body": response.get("body"),
        "body_text": response.get("body_text"),
    }


def run_operation(
    base_url: str,
    operation: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    response = request_json(
        base_url,
        operation["method"],
        operation["path"],
        operation.get("body"),
        timeout,
    )
    return {
        "name": operation["name"],
        "method": operation["method"],
        "path": operation["path"],
        **response,
    }


def run_operation_with_resume(
    base_url: str,
    operation: dict[str, Any],
    timeout: float,
    target: str,
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    operation_key = f"{target}:{operation['name']}"
    operation_records = checkpoint.setdefault("operation_records", {})
    if operation_key in set(checkpoint.get("completed_operations", [])):
        cached = operation_records.get(operation_key, {})
        return {
            "name": operation["name"],
            "method": operation["method"],
            "path": operation["path"],
            "target": target,
            "skipped": True,
            **cached,
        }
    step = run_operation(base_url, operation, timeout)
    step["target"] = target
    step["skipped"] = False
    checkpoint.setdefault("completed_operations", []).append(operation_key)
    operation_records[operation_key] = {
        "status": step.get("status"),
        "body": step.get("body"),
        "body_text": step.get("body_text"),
    }
    return step


def run_check(
    base_url: str,
    check: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    if "steps" not in check:
        response = request_json(
            base_url,
            check["method"],
            check["path"],
            check.get("body"),
            timeout,
        )
        return summarize_response(check, response)

    previous_response: dict[str, Any] | None = None
    step_summaries: list[dict[str, Any]] = []
    for step in check["steps"]:
        response = request_json(
            base_url,
            step["method"],
            step["path"],
            materialize_template(step.get("body"), previous_response),
            timeout,
        )
        previous_response = response
        step_summaries.append(
            {
                "name": step["name"],
                "summary": summarize_response(
                    {
                        "extract": step.get("extract"),
                        "compare_paths": step.get("compare_paths", []),
                    },
                    response,
                ),
            }
        )
    return {
        "steps": step_summaries,
        "final": step_summaries[-1]["summary"] if step_summaries else {},
    }


def legacy_fixture_to_operations_and_checks(fixture: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    index = fixture["index"]
    operations: list[dict[str, Any]] = [
        {
            "name": "create_index",
            "method": "PUT",
            "path": f"/{index}",
            "body": {
                "settings": fixture["settings"],
                "mappings": fixture["mappings"],
            },
        }
    ]
    for entry in fixture["docs"]:
        operations.append(
            {
                "name": f"put_{entry['id']}",
                "method": "PUT",
                "path": f"/{index}/_doc/{entry['id']}?refresh=wait_for",
                "body": entry["source"],
            }
        )
    checks = [
        {
            "name": "index_search",
            "method": "POST",
            "path": f"/{index}/_search",
            "body": fixture["query"],
            "extract": "search_summary",
        }
    ]
    return operations, checks


def main() -> int:
    args = parse_args()
    if not args.steelsearch_url or not args.opensearch_url:
        print("Both STEELSEARCH_URL and OPENSEARCH_URL are required", file=sys.stderr)
        return 2

    fixture = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    operations = fixture.get("operations")
    checks = fixture.get("checks")
    preflight_checks = fixture.get("preflight_checks", [])
    if operations is None or checks is None:
        operations, checks = legacy_fixture_to_operations_and_checks(fixture)

    report: dict[str, Any] = {
        "name": fixture.get("name", "migration-cutover-integration"),
        "fixture": str(Path(args.fixture).resolve()),
        "source": args.opensearch_url,
        "target": args.steelsearch_url,
        "resume": {},
        "steps": [],
        "preflight": [],
        "checks": [],
        "comparison": {},
    }
    checkpoint_path = Path(args.checkpoint)
    checkpoint = load_checkpoint(checkpoint_path)
    report["resume"] = {
        "checkpoint": str(checkpoint_path.resolve()),
        "resumed": bool(checkpoint.get("completed_operations")),
        "completed_operations_before_run": list(checkpoint.get("completed_operations", [])),
    }

    for operation in operations:
        source_step = run_operation_with_resume(
            args.opensearch_url,
            operation,
            args.timeout,
            "source",
            checkpoint,
        )
        report["steps"].append(source_step)
        save_checkpoint(checkpoint_path, checkpoint)

    preflight_blocked = False
    for check in preflight_checks:
        source_summary = run_check(args.opensearch_url, check, args.timeout)
        blockers = source_summary.get("blockers") or []
        blocked = bool(check.get("must_block") and blockers)
        report["preflight"].append(
            {
                "name": check["name"],
                "source": source_summary,
                "must_block": bool(check.get("must_block")),
                "blocked": blocked,
            }
        )
        if blocked:
            preflight_blocked = True

    if preflight_blocked:
        report["comparison"] = {
            "match": False,
            "blocked_by_preflight": True,
            "checks": [],
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        report["resume"]["completed_operations_after_run"] = list(
            checkpoint.get("completed_operations", [])
        )
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1

    for operation in operations:
        target_step = run_operation_with_resume(
            args.steelsearch_url,
            operation,
            args.timeout,
            "target",
            checkpoint,
        )
        report["steps"].append(target_step)
        save_checkpoint(checkpoint_path, checkpoint)

    for check in checks:
        source_summary = run_check(args.opensearch_url, check, args.timeout)
        target_summary = run_check(args.steelsearch_url, check, args.timeout)
        report["checks"].append(
            {
                "name": check["name"],
                "source": source_summary,
                "target": target_summary,
                "match": source_summary == target_summary,
            }
        )

    overall_match = all(check["match"] for check in report["checks"])
    report["comparison"] = {
        "match": overall_match,
        "checks": report["checks"],
    }
    if report["checks"]:
        report["comparison"]["source"] = report["checks"][0]["source"]
        report["comparison"]["target"] = report["checks"][0]["target"]

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    report["resume"]["completed_operations_after_run"] = list(
        checkpoint.get("completed_operations", [])
    )
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if overall_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
