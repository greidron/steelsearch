#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
import json
from pathlib import Path

from runtime_route_normalization import is_concrete_path, normalize_path


ROOT = Path("/home/ubuntu/steelsearch")
REST_TSV = ROOT / "docs/rust-port/generated/source-rest-routes.tsv"
TRANSPORT_TSV = ROOT / "docs/rust-port/generated/source-transport-actions.tsv"
OUT_DIR = ROOT / "docs/api-spec/generated"
GENERATED_ARTIFACTS = [
    OUT_DIR / "rest-routes.md",
    OUT_DIR / "transport-actions.md",
    OUT_DIR / "route-evidence-matrix.md",
    OUT_DIR / "openapi.json",
]
RUNTIME_ROUTE_LEDGER = OUT_DIR / "runtime-route-ledger.json"
STATEFUL_ROUTE_PROBE_REPORT = OUT_DIR / "runtime-stateful-route-probe-report.json"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


def include_rest_row(row: dict[str, str]) -> bool:
    return not (
        row["method"] == "DELETE"
        and row["path_or_expression"] == "/"
        and row["source"].endswith("RestDeleteIndexAction.java")
    ) and not (
        "/_opensearch_dashboards" in row["path_or_expression"]
        and "route.getPath(" in row["path_or_expression"]
    )


def rest_family(row: dict[str, str]) -> str:
    src = row["source"]
    path = row["path_or_expression"]
    if path in {"/", ""} or path.startswith("/_cluster") or path.startswith("/_nodes") or path.startswith("/_cat") or path.startswith("/_tasks"):
        return "root-cluster-node"
    if "/admin/cluster/" in src:
        return "root-cluster-node"
    if "/cat/" in src:
        return "root-cluster-node"
    if "/admin/indices/" in src:
        if any(token in path for token in ("/_search", "/_msearch", "/_pit", "/_rank_eval", "/_validate/query")):
            return "search"
        if any(token in path for token in ("/_refresh", "/_doc", "/_bulk", "/_update", "/_delete_by_query", "/_update_by_query", "/_reindex")):
            return "document-and-bulk"
        return "index-and-metadata"
    if "/document/" in src or "/bulk/" in src:
        return "document-and-bulk"
    if "/search/" in src:
        return "search"
    if "/modules/lang-mustache/" in src or "/modules/rank-eval/" in src:
        return "search"
    if "/modules/reindex/" in src:
        return "document-and-bulk"
    if "/ingest/" in src or "/script/" in src or "/repositories/" in src:
        return "snapshot-migration-interop"
    if "/knn/" in src or "/_plugins/_knn" in path or "/_plugins/_ml" in path:
        return "vector-and-ml"
    if any(token in path for token in ("/_snapshot", "/_scripts", "/_ingest", "/_remote", "/_decommission", "/_plugins/_ml")):
        return "snapshot-migration-interop"
    return "misc"


def transport_family(row: dict[str, str]) -> str:
    action = row["action"]
    if any(token in action for token in ("Snapshot", "Repository", "Dangling", "Decommission", "RemoteStore")):
        return "snapshot-migration-interop"
    if any(token in action for token in ("KNN", "Model", "Training", "ClearCache")):
        return "vector-and-ml"
    if any(token in action for token in ("Search", "Pit", "Explain", "RankEval", "Suggest")):
        return "search"
    if any(token in action for token in ("Index", "Delete", "Update", "Bulk", "Refresh", "Reindex", "DeleteByQuery", "UpdateByQuery")):
        return "document-and-bulk"
    if any(token in action for token in ("Cluster", "Nodes", "Task", "Voting", "Wlm", "MainAction")):
        return "root-cluster-node"
    return "index-and-metadata"


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def status_behavior(status: str) -> str:
    return {
        "implemented": "Steelsearch exposes this surface with the main supported behavior present.",
        "implemented-read": "Steelsearch exposes this safe read/head surface in the standalone runtime; deeper parity may still remain.",
        "implemented-stateful": "Steelsearch exposes this stateful surface in the standalone runtime; deeper parity and compare coverage may still remain.",
        "partial": "Steelsearch exposes this surface, but the behavior is narrower than OpenSearch.",
        "stubbed": "Steelsearch exposes an OpenSearch-shaped shell or development-only subset here.",
        "planned": "OpenSearch exposes this surface, but Steelsearch has not implemented it yet.",
        "out-of-scope": "This surface is explicitly excluded from the current standalone Steelsearch target.",
    }.get(status, "Current behavior is not yet classified beyond the source inventory.")


def rest_meaning(method: str, path: str, source: str) -> str:
    if path == "/" and method == "GET":
        return "Returns root node identity and version metadata."
    if path == "/" and method == "HEAD":
        return "Returns a bodyless liveness-style success response at the root path."
    if path.startswith("/_cluster/health"):
        return "Returns cluster health, shard availability, and optional wait semantics."
    if path.startswith("/_cluster/state"):
        return "Returns cluster-state metadata, routing, and selected filtered views."
    if path.startswith("/_cluster/settings"):
        return "Reads or mutates cluster-level settings."
    if path.startswith("/_cluster/allocation/explain"):
        return "Explains shard allocation or allocation failure reasons."
    if path.startswith("/_cluster/reroute"):
        return "Requests explicit shard reroute or allocation changes."
    if path.startswith("/_nodes/stats"):
        return "Returns node runtime, index, transport, and cache statistics."
    if path.startswith("/_nodes") and "hot_threads" in path:
        return "Returns diagnostic hot-thread output for node debugging."
    if path.startswith("/_nodes") and "usage" in path:
        return "Returns node feature and API usage counters."
    if path.startswith("/_tasks"):
        return "Lists, inspects, or cancels long-running cluster tasks."
    if path.startswith("/_cat"):
        return "Returns operator-oriented cat output for cluster or index summaries."
    if path == "/{index}" and method == "PUT":
        return "Creates an index with mappings, settings, and alias metadata."
    if path == "/{index}" and method == "GET":
        return "Reads index existence and index metadata."
    if path == "/{index}" and method == "HEAD":
        return "Checks whether a target index exists without returning a body."
    if path == "/{index}" and method == "DELETE":
        return "Deletes an index and its metadata."
    if "/_mapping" in path and "field" not in path and method == "GET":
        return "Returns mappings for one or more indices."
    if "/_mapping" in path and method in {"PUT", "POST"}:
        return "Mutates mappings for target indices."
    if "/_mapping/field/" in path:
        return "Returns mapping information for specific fields."
    if "/_settings" in path and method == "GET":
        return "Returns effective settings for target indices."
    if "/_settings" in path and method in {"PUT", "POST"}:
        return "Mutates mutable settings for target indices."
    if "/_alias" in path or "/_aliases" in path:
        return "Reads or mutates alias definitions and alias-to-index mapping."
    if "/_component_template" in path or "/_index_template" in path or path.startswith("/_template"):
        return "Reads or mutates index-template metadata used for future index creation."
    if path.startswith("/_data_stream"):
        return "Reads or mutates data stream lifecycle and backing-index state."
    if "/_rollover" in path:
        return "Rolls a write target to a new backing index under configured conditions."
    if "/_refresh" in path:
        return "Forces recent writes to become visible for search."
    if "/_bulk" in path:
        return "Executes NDJSON bulk write operations across one or more indices."
    if "/_doc/" in path and method == "GET":
        return "Fetches a single document by id."
    if "/_doc/" in path and method in {"PUT", "POST"}:
        return "Indexes, replaces, or creates a single document."
    if "/_doc/" in path and method == "DELETE":
        return "Deletes a single document by id."
    if "/_update" in path:
        return "Partially updates documents, often with script or upsert behavior."
    if "/_search" in path and "/_search/template" not in path and "/_search_shards" not in path:
        return "Executes search requests with Query DSL, sorting, pagination, and aggregations."
    if "/_msearch" in path:
        return "Executes multiple search requests in one API call."
    if "/_search/template" in path or "/_render/template" in path:
        return "Executes or renders mustache-backed search templates."
    if "/_pit" in path:
        return "Creates, lists, inspects, or deletes point-in-time search handles."
    if "/_scripts" in path or "/_script_" in path:
        return "Reads, mutates, or executes stored or runtime script surfaces."
    if "/_snapshot" in path:
        return "Reads, mutates, verifies, creates, deletes, or restores snapshot repository state."
    if "/_reindex" in path or "/_update_by_query" in path or "/_delete_by_query" in path:
        return "Runs bulk document rewrite or migration-style operations over query results."
    if "/_plugins/_knn" in path:
        return "Exposes k-NN plugin operational, cache, training, and model routes."
    if "/_plugins/_ml" in path:
        return "Exposes ML Commons model, task, prediction, and deployment routes."
    if "/_ingest" in path:
        return "Reads, mutates, or inspects ingest processors and ingest pipelines."
    if "/_remote" in path or "Remote" in source:
        return "Exposes remote-cluster or remote-store operational state."
    if "/_decommission" in path:
        return "Exposes decommission lifecycle and awareness-removal controls."
    if "/_validate/query" in path:
        return "Validates a query request without fully executing it."
    if "/_segments" in path:
        return "Returns Lucene segment-level details for index shards."
    if "/_shard_stores" in path:
        return "Returns shard-store availability and copy information."
    if "/_recovery" in path:
        return "Returns shard recovery progress and recovery metadata."
    return "OpenSearch exposes this REST surface; semantics should be confirmed from the referenced source handler."


def rest_gap(status: str, family: str, path: str) -> str:
    if status == "implemented":
        return "Remaining gaps are mostly parity depth, option coverage, and production-hardening."
    if status == "implemented-read":
        return "Read-path routing is present in the standalone runtime; parity depth, option coverage, and compare fixtures may still remain."
    if status == "implemented-stateful":
        return "Stateful route handling is present in the standalone runtime; deeper mutation semantics, error parity, and compare fixtures may still remain."
    if status == "stubbed":
        return "Steelsearch needs full OpenSearch semantics, not only a development shell."
    if status == "planned":
        return "Steelsearch still needs route implementation, error-shape parity, and compatibility tests."
    if status == "out-of-scope":
        return "This route stays outside the current replacement target unless scope changes."
    if family == "search":
        return "Search-family gaps usually include advanced request options, response shaping, and shard-phase parity."
    if family == "document-and-bulk":
        return "Write-family gaps usually include routing, versioning, conflict behavior, and full replica semantics."
    if family == "index-and-metadata":
        return "Metadata-family gaps usually include templates, aliases, settings, wildcard behavior, and lifecycle semantics."
    if family == "root-cluster-node":
        return "Operational parity still needs production tasking, telemetry depth, allocation logic, and cluster coordination."
    return "Parity and behavioral coverage remain incomplete."


def transport_meaning(action: str) -> str:
    text = action.replace(".INSTANCE", "")
    if "ClusterHealth" in text:
        return "Cluster-health transport action used by admin and health callers."
    if "ClusterState" in text:
        return "Cluster-state transport action used to read authoritative cluster metadata."
    if "Nodes" in text and "Stats" in text:
        return "Node statistics transport action."
    if "Nodes" in text and "Info" in text:
        return "Node info transport action."
    if "Task" in text:
        return "Transport action for task listing, lookup, completion, or cancellation."
    if "Search" in text or "Pit" in text or "Suggest" in text or "RankEval" in text:
        return "Transport action used by search or search-adjacent features."
    if "Bulk" in text or "Index" in text or "Update" in text or "Delete" in text or "Refresh" in text:
        return "Transport action used by write-path or document lifecycle features."
    if "Snapshot" in text or "Repository" in text or "Dangling" in text or "RemoteStore" in text:
        return "Transport action used by repository, snapshot, remote-store, or restore flows."
    if "KNN" in text or "Model" in text or "Training" in text or "Cache" in text:
        return "Transport action used by vector-search or model-serving plugin flows."
    return "OpenSearch transport action that still needs explicit compatibility treatment."


def transport_gap(status: str, family: str) -> str:
    if status == "planned":
        return "Steelsearch still needs Java-compatible request/response handling and fail-closed validation here."
    if status == "out-of-scope":
        return "This transport surface is outside the current standalone replacement target."
    if family == "search":
        return "Search transport parity still needs named-writeable coverage, request serialization, and response parity."
    if family == "document-and-bulk":
        return "Write transport parity still needs sequencing, replication semantics, and conflict behavior."
    if family == "root-cluster-node":
        return "Operational transport parity still needs admin runtime, tasking, and cluster-coordination semantics."
    return "Transport parity remains incomplete."


def render_rest_reference(rows: list[dict[str, str]]) -> str:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[rest_family(row)].append(row)

    parts = [
        "# Generated REST Route Reference",
        "",
        "This file is generated from `docs/rust-port/generated/source-rest-routes.tsv`.",
        "It is exhaustive at the source-inventory level and should be treated as",
        "the route-by-route companion to the hand-written API specs.",
        "",
        "Columns:",
        "",
        "- `status`: current Steelsearch classification from the source compatibility matrix",
        "- `method`: HTTP method captured from the OpenSearch registration site",
        "- `path_or_expression`: registered route or source expression",
        "- `opensearch_meaning`: semantic intent of the route in OpenSearch",
        "- `steelsearch_behavior`: current Steelsearch implementation posture derived from status and known docs",
        "- `replacement_gap`: what still blocks full replacement semantics",
        "- `source`: OpenSearch source file",
        "- `line`: source line used by the inventory",
        "",
    ]

    order = [
        "root-cluster-node",
        "index-and-metadata",
        "document-and-bulk",
        "search",
        "vector-and-ml",
        "snapshot-migration-interop",
        "misc",
    ]
    for family in order:
        family_rows = grouped.get(family)
        if not family_rows:
            continue
        parts.extend(
            [
                f"## {family}",
                "",
                "| status | method | path_or_expression | opensearch_meaning | steelsearch_behavior | replacement_gap | source | line |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in family_rows:
            source = Path(row["source"]).name
            path = row["path_or_expression"].replace("|", "\\|")
            meaning = rest_meaning(row["method"], row["path_or_expression"], row["source"]).replace("|", "\\|")
            behavior = status_behavior(row["status"]).replace("|", "\\|")
            gap = rest_gap(row["status"], family, row["path_or_expression"]).replace("|", "\\|")
            parts.append(
                f"| {row['status']} | {row['method'] or '(dynamic)'} | `{path}` | {meaning} | {behavior} | {gap} | `{source}` | {row['line']} |"
            )
        parts.append("")
    return "\n".join(parts)


def render_transport_reference(rows: list[dict[str, str]]) -> str:
    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[transport_family(row)].append(row)

    parts = [
        "# Generated Transport Action Reference",
        "",
        "This file is generated from `docs/rust-port/generated/source-transport-actions.tsv`.",
        "It is exhaustive at the transport-action inventory level.",
        "",
        "Columns:",
        "",
        "- `status`: current Steelsearch classification from the source compatibility matrix",
        "- `action`: OpenSearch action identifier",
        "- `transport_handler`: Java transport handler class registered for the action",
        "- `opensearch_meaning`: semantic role of the action inside OpenSearch",
        "- `steelsearch_behavior`: current Steelsearch implementation posture derived from status and docs",
        "- `replacement_gap`: what still blocks parity",
        "",
    ]
    order = [
        "root-cluster-node",
        "index-and-metadata",
        "document-and-bulk",
        "search",
        "vector-and-ml",
        "snapshot-migration-interop",
    ]
    for family in order:
        family_rows = grouped.get(family)
        if not family_rows:
            continue
        parts.extend(
            [
                f"## {family}",
                "",
                "| status | action | transport_handler | opensearch_meaning | steelsearch_behavior | replacement_gap | source | line |",
                "| --- | --- | --- | --- | --- | --- | --- | --- |",
            ]
        )
        for row in family_rows:
            source = Path(row["source"]).name
            handler = row["transport_handler"].replace("|", "\\|")
            action = row["action"].replace("|", "\\|")
            meaning = transport_meaning(row["action"]).replace("|", "\\|")
            behavior = status_behavior(row["status"]).replace("|", "\\|")
            gap = transport_gap(row["status"], family).replace("|", "\\|")
            parts.append(
                f"| {row['status']} | `{action}` | `{handler}` | {meaning} | {behavior} | {gap} | `{source}` | {row['line']} |"
            )
        parts.append("")
    return "\n".join(parts)


def rest_evidence_owner(row: dict[str, str]) -> tuple[str, str]:
    family = rest_family(row)
    status = row["status"]
    if status in {"planned", "out-of-scope"}:
        return ("deferred", "no canonical runtime compare owner")
    if family == "root-cluster-node":
        return ("root-cluster-node", "tools/run-phase-a-acceptance-harness.sh --scope root-cluster-node")
    if family == "index-and-metadata":
        return ("index-metadata", "tools/run-phase-a-acceptance-harness.sh --scope index-metadata")
    if family == "document-and-bulk":
        return ("document-write-path", "tools/run-phase-a-acceptance-harness.sh --scope document-write-path")
    if family == "search":
        return ("search", "tools/run-phase-a-acceptance-harness.sh --scope search")
    if family == "snapshot-migration-interop":
        return ("snapshot-migration", "tools/run-phase-a-acceptance-harness.sh --scope snapshot-migration")
    if family == "vector-and-ml":
        return ("vector-ml", "tools/run-phase-a-acceptance-harness.sh --scope vector-ml")
    return ("deferred", "no canonical runtime compare owner")


def load_runtime_route_ledger() -> dict[tuple[str, str], str]:
    if not RUNTIME_ROUTE_LEDGER.exists():
        return {}
    payload = json.loads(RUNTIME_ROUTE_LEDGER.read_text(encoding="utf-8"))
    mapping: dict[tuple[str, str], str] = {}
    for route in payload.get("routes", []):
        method = route.get("method")
        path = route.get("path")
        runtime_status = route.get("runtime_status")
        if not method or not path or not runtime_status:
            continue
        mapping[(method, path)] = runtime_status
        normalized_path = normalize_openapi_path(path)
        if normalized_path is not None:
            mapping[(method, normalized_path)] = runtime_status
    return mapping


def load_stateful_route_report() -> dict[tuple[str, str], str]:
    if not STATEFUL_ROUTE_PROBE_REPORT.exists():
        return {}
    payload = json.loads(STATEFUL_ROUTE_PROBE_REPORT.read_text(encoding="utf-8"))
    mapping: dict[tuple[str, str], str] = {}
    for case in payload.get("cases", []):
        method = case.get("method")
        inventory_path = case.get("inventory_path")
        runtime_status = case.get("runtime_status")
        if not method or not inventory_path or not runtime_status:
            continue
        mapping[(method, inventory_path)] = runtime_status
    return mapping


def apply_runtime_route_status(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ledger = load_runtime_route_ledger()
    stateful_report = load_stateful_route_report()
    if not ledger and not stateful_report:
        return rows
    updated: list[dict[str, str]] = []
    for row in rows:
        next_row = dict(row)
        normalized_path = normalize_openapi_path(row["path_or_expression"])
        runtime_status = ledger.get((row["method"], row["path_or_expression"]))
        if runtime_status is None and normalized_path is not None:
            runtime_status = ledger.get((row["method"], normalized_path))
        if runtime_status == "implemented-read" and row["status"] in {"planned", "stubbed"}:
            next_row["status"] = "implemented-read"
        stateful_status = stateful_report.get((row["method"], row["path_or_expression"]))
        if stateful_status is None and normalized_path is not None:
            stateful_status = stateful_report.get((row["method"], normalized_path))
        if stateful_status == "stateful-route-present" and row["status"] in {"planned", "stubbed"}:
            next_row["status"] = "implemented-stateful"
        updated.append(next_row)
    return updated


def render_route_evidence_matrix(rows: list[dict[str, str]]) -> str:
    parts = [
        "# Generated Route Evidence Matrix",
        "",
        "This file maps each source-derived REST route to its current Steelsearch",
        "status and the canonical comparison/profile owner when one exists.",
        "",
        "| family | status | method | path_or_expression | evidence_profile | evidence_entrypoint |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in rows:
        family = rest_family(row)
        profile, entrypoint = rest_evidence_owner(row)
        path = row["path_or_expression"].replace("|", "\\|")
        parts.append(
            f"| {family} | {row['status']} | {row['method'] or '(dynamic)'} | `{path}` | `{profile}` | `{entrypoint}` |"
        )
    parts.append("")
    return "\n".join(parts)


def normalize_openapi_path(path: str) -> str | None:
    normalized = normalize_path(path)
    if not is_concrete_path(normalized):
        return None
    return normalized


def openapi_tags() -> list[dict[str, str]]:
    return [
        {
            "name": "root-cluster-node",
            "description": "Root, cluster, node, cat, task, and operational admin routes.",
        },
        {
            "name": "index-and-metadata",
            "description": "Index lifecycle, mappings, settings, aliases, templates, and data streams.",
        },
        {
            "name": "document-and-bulk",
            "description": "Single-document CRUD, bulk, refresh, and write-path routes.",
        },
        {
            "name": "search",
            "description": "Search, search session, query validation, and rank-eval routes.",
        },
        {
            "name": "vector-and-ml",
            "description": "k-NN and ML/model-serving plugin routes.",
        },
        {
            "name": "snapshot-migration-interop",
            "description": "Snapshot, migration, repository, ingest, and script-adjacent routes.",
        },
        {
            "name": "misc",
            "description": "Source-derived routes that do not fit the primary family buckets.",
        },
    ]


def parameter_schema_for(name: str) -> dict:
    integer_like = {
        "shard",
        "from",
        "size",
        "k",
        "num_candidates",
        "pre_filter_shard_size",
    }
    boolean_like = {
        "pretty",
        "human",
        "v",
        "local",
        "include_defaults",
        "ignore_unavailable",
        "allow_no_indices",
        "track_total_hits",
    }
    if name in integer_like:
        return {"type": "integer"}
    if name in boolean_like:
        return {"type": "boolean"}
    return {"type": "string"}


def path_parameters(path: str) -> list[dict]:
    parameters = []
    for segment in path.split("/"):
        if segment.startswith("{") and segment.endswith("}"):
            name = segment[1:-1]
            parameters.append(
                {
                    "name": name,
                    "in": "path",
                    "required": True,
                    "schema": parameter_schema_for(name),
                }
            )
    return parameters


def query_parameters(path: str, method: str) -> list[dict]:
    params: list[dict] = []
    if method in {"get", "post"} and (path == "/_search" or "/_search" in path):
        params.extend(
            [
                {"name": "from", "in": "query", "required": False, "schema": {"type": "integer"}},
                {"name": "size", "in": "query", "required": False, "schema": {"type": "integer"}},
                {
                    "name": "track_total_hits",
                    "in": "query",
                    "required": False,
                    "schema": {"type": "boolean"},
                },
            ]
        )
    if "/_cluster/health" in path:
        params.extend(
            [
                {"name": "wait_for_status", "in": "query", "required": False, "schema": {"type": "string"}},
                {"name": "timeout", "in": "query", "required": False, "schema": {"type": "string"}},
            ]
        )
    if "/_snapshot" in path:
        params.append(
            {"name": "ignore_unavailable", "in": "query", "required": False, "schema": {"type": "boolean"}}
        )
    deduped = []
    seen = set()
    for param in params:
        key = (param["name"], param["in"])
        if key not in seen:
            seen.add(key)
            deduped.append(param)
    return deduped


def include_openapi_operation(row: dict[str, str], path: str, method: str) -> bool:
    source = row["source"]
    status = row["status"]
    if "/plugins/examples/" in source:
        return False
    if path == "/" and method not in {"get", "head"}:
        return False
    if path.startswith("/_cat") and method != "get":
        return False
    if status == "out-of-scope" and path.startswith("/_cat/example"):
        return False
    return True


def operation_id(method: str, path: str) -> str:
    pieces = []
    for segment in path.strip("/").split("/"):
        if not segment:
            continue
        if segment.startswith("{") and segment.endswith("}"):
            pieces.append("by_" + segment[1:-1].replace("-", "_"))
        else:
            pieces.append(
                segment.replace("-", "_").replace(".", "_").replace("*", "wildcard")
            )
    suffix = "_".join(pieces) if pieces else "root"
    return f"{method}_{suffix}"


def request_body_for(path: str, method: str) -> dict | None:
    if method not in {"post", "put"}:
        return None
    if path in {"/_bulk", "/_bulk/stream"} or path.endswith("/_bulk"):
        return {
            "required": False,
            "content": {
                "application/x-ndjson": {
                    "schema": {"$ref": "#/components/schemas/BulkNdjsonRequest"}
                }
            },
        }
    return {
        "required": False,
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/OpenSearchJsonRequest"}
            }
        },
    }


CAT_RESPONSE_SCHEMAS = {
    "/_cat/aliases": "CatAliasesResponse",
    "/_cat/allocation": "CatAllocationResponse",
    "/_cat/count": "CatCountResponse",
    "/_cat/fielddata": "CatFielddataResponse",
    "/_cat/health": "CatHealthResponse",
    "/_cat/indices": "CatIndicesResponse",
    "/_cat/nodeattrs": "CatNodeAttrsResponse",
    "/_cat/nodes": "CatNodesResponse",
    "/_cat/pending_tasks": "CatPendingTasksResponse",
    "/_cat/pit_segments": "CatPitSegmentsResponse",
    "/_cat/plugins": "CatPluginsResponse",
    "/_cat/recovery": "CatRecoveryResponse",
    "/_cat/repositories": "CatRepositoriesResponse",
    "/_cat/segments": "CatSegmentsResponse",
    "/_cat/shards": "CatShardsResponse",
    "/_cat/snapshots": "CatSnapshotsResponse",
    "/_cat/tasks": "CatTasksResponse",
    "/_cat/templates": "CatTemplatesResponse",
    "/_cat/thread_pool": "CatThreadPoolResponse",
}


def cat_schema_name_for(path: str) -> str | None:
    if path == "/_cat":
        return None
    for prefix, schema_name in CAT_RESPONSE_SCHEMAS.items():
        if path == prefix or path.startswith(prefix + "/"):
            return schema_name
    return "CatJsonRowsResponse"


def success_schema_for(path: str, method: str) -> dict:
    if method == "head":
        return {"$ref": "#/components/schemas/EmptySuccessResponse"}
    if path.startswith("/_cat"):
        schema_name = cat_schema_name_for(path)
        if schema_name is None:
            return {"type": "string"}
        return {"$ref": f"#/components/schemas/{schema_name}"}
    return {"$ref": "#/components/schemas/OpenSearchSuccessEnvelope"}


def success_content_for(path: str, method: str) -> dict:
    success_schema = success_schema_for(path, method)
    if method == "head":
        return {}
    if path.startswith("/_cat"):
        if path == "/_cat":
            return {
                "text/plain": {"schema": {"type": "string"}},
            }
        return {
            "application/json": {"schema": success_schema},
            "text/plain": {"schema": {"type": "string"}},
        }
    if "hot_threads" in path:
        return {
            "text/plain": {"schema": {"type": "string"}},
        }
    return {
        "application/json": {"schema": success_schema},
    }


def responses_for(path: str, method: str) -> dict:
    return {
        "200": {
            "description": "Successful response envelope",
            "content": success_content_for(path, method),
        },
        "400": {
            "description": "OpenSearch-shaped fail-closed error",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/OpenSearchErrorResponse"}
                }
            },
        },
        "404": {
            "description": "Not found",
            "content": {
                "application/json": {
                    "schema": {"$ref": "#/components/schemas/OpenSearchErrorResponse"}
                }
            },
        },
    }


def generate_openapi(rows: list[dict[str, str]]) -> dict:
    spec: dict[str, object] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Steelsearch API",
            "version": "0.1.0",
            "description": (
                "Generated OpenAPI companion built from the source-derived REST route "
                "inventory. This reflects route inventory and evidence ownership, not "
                "a claim that every listed route is fully implemented."
            ),
        },
        "servers": [{"url": "/"}],
        "tags": openapi_tags(),
        "components": {
            "schemas": {
                "OpenSearchJsonRequest": {"type": "object", "additionalProperties": True},
                "BulkNdjsonRequest": {"type": "string", "description": "NDJSON bulk request body."},
                "OpenSearchSuccessEnvelope": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Generic OpenSearch-shaped success response."
                },
                "EmptySuccessResponse": {
                    "type": "object",
                    "description": "Bodyless or empty success response."
                },
                "CatJsonRow": {
                    "type": "object",
                    "additionalProperties": True,
                    "description": "Generic JSON row emitted by a cat API."
                },
                "CatJsonRowsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatJsonRow"},
                    "description": "JSON response emitted by a cat API when format=json is requested."
                },
                "CatCountRow": {
                    "type": "object",
                    "properties": {
                        "epoch": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "count": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat count API."
                },
                "CatCountResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatCountRow"},
                    "description": "JSON response emitted by the cat count API."
                },
                "CatAliasRow": {
                    "type": "object",
                    "properties": {
                        "alias": {"type": "string"},
                        "index": {"type": "string"},
                        "filter": {"type": "string"},
                        "routing.index": {"type": "string"},
                        "routing.search": {"type": "string"},
                        "is_write_index": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat aliases API."
                },
                "CatAliasesResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatAliasRow"},
                    "description": "JSON response emitted by the cat aliases API."
                },
                "CatAllocationRow": {
                    "type": "object",
                    "properties": {
                        "shards": {"type": "string"},
                        "shards.undesired": {"type": "string"},
                        "disk.indices": {"type": "string"},
                        "disk.used": {"type": "string"},
                        "disk.avail": {"type": "string"},
                        "disk.total": {"type": "string"},
                        "disk.percent": {"type": "string"},
                        "host": {"type": "string"},
                        "host": {"type": "string"},
                        "ip": {"type": "string"},
                        "node": {"type": "string"},
                        "node.role": {"type": "string"},
                        "node.roles": {"type": "string"},
                        "node": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat allocation API."
                },
                "CatAllocationResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatAllocationRow"},
                    "description": "JSON response emitted by the cat allocation API."
                },
                "CatFielddataRow": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "host": {"type": "string"},
                        "ip": {"type": "string"},
                        "node": {"type": "string"},
                        "field": {"type": "string"},
                        "size": {"type": "string"},
                        "evictions": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat fielddata API."
                },
                "CatFielddataResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatFielddataRow"},
                    "description": "JSON response emitted by the cat fielddata API."
                },
                "CatHealthRow": {
                    "type": "object",
                    "properties": {
                        "epoch": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "cluster": {"type": "string"},
                        "status": {"type": "string"},
                        "node.total": {"type": "string"},
                        "node.data": {"type": "string"},
                        "shards": {"type": "string"},
                        "pri": {"type": "string"},
                        "relo": {"type": "string"},
                        "init": {"type": "string"},
                        "unassign": {"type": "string"},
                        "pending_tasks": {"type": "string"},
                        "task_max_waiting_in_queue_millis": {"type": "string"},
                        "max_task_wait_time": {"type": "string"},
                        "active_shards_percent": {"type": "string"},
                        "discovered_cluster_manager": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat health API."
                },
                "CatHealthResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatHealthRow"},
                    "description": "JSON response emitted by the cat health API."
                },
                "CatIndexRow": {
                    "type": "object",
                    "properties": {
                        "health": {"type": "string"},
                        "status": {"type": "string"},
                        "index": {"type": "string"},
                        "uuid": {"type": "string"},
                        "pri": {"type": "string"},
                        "rep": {"type": "string"},
                        "docs.count": {"type": "string"},
                        "docs.deleted": {"type": "string"},
                        "creation.date": {"type": "string"},
                        "creation.date.string": {"type": "string"},
                        "store.size": {"type": "string"},
                        "pri.store.size": {"type": "string"},
                        "dataset.size": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat indices API."
                },
                "CatIndicesResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatIndexRow"},
                    "description": "JSON response emitted by the cat indices API."
                },
                "CatNodeAttrRow": {
                    "type": "object",
                    "properties": {
                        "node": {"type": "string"},
                        "host": {"type": "string"},
                        "ip": {"type": "string"},
                        "attr": {"type": "string"},
                        "value": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat nodeattrs API."
                },
                "CatNodeAttrsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatNodeAttrRow"},
                    "description": "JSON response emitted by the cat nodeattrs API."
                },
                "CatNodeRow": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "pid": {"type": "string"},
                        "ip": {"type": "string"},
                        "port": {"type": "string"},
                        "http_address": {"type": "string"},
                        "version": {"type": "string"},
                        "type": {"type": "string"},
                        "build": {"type": "string"},
                        "jdk": {"type": "string"},
                        "disk.total": {"type": "string"},
                        "disk.used": {"type": "string"},
                        "disk.avail": {"type": "string"},
                        "disk.used_percent": {"type": "string"},
                        "heap.percent": {"type": "string"},
                        "heap.current": {"type": "string"},
                        "heap.max": {"type": "string"},
                        "ram.percent": {"type": "string"},
                        "ram.current": {"type": "string"},
                        "ram.max": {"type": "string"},
                        "cpu": {"type": "string"},
                        "load_1m": {"type": "string"},
                        "load_5m": {"type": "string"},
                        "load_15m": {"type": "string"},
                        "node.role": {"type": "string"},
                        "node.roles": {"type": "string"},
                        "cluster_manager": {"type": "string"},
                        "name": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat nodes API."
                },
                "CatNodesResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatNodeRow"},
                    "description": "JSON response emitted by the cat nodes API."
                },
                "CatPendingTaskRow": {
                    "type": "object",
                    "properties": {
                        "insertOrder": {"type": "string"},
                        "timeInQueue": {"type": "string"},
                        "priority": {"type": "string"},
                        "executing": {"type": "string"},
                        "time_in_queue_millis": {"type": "string"},
                        "priority": {"type": "string"},
                        "source": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat pending tasks API."
                },
                "CatPendingTasksResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatPendingTaskRow"},
                    "description": "JSON response emitted by the cat pending tasks API."
                },
                "CatPitSegmentRow": {
                    "type": "object",
                    "properties": {
                        "pit_id": {"type": "string"},
                        "index": {"type": "string"},
                        "shard": {"type": "string"},
                        "segment": {"type": "string"},
                        "generation": {"type": "string"},
                        "docs.count": {"type": "string"},
                        "docs.deleted": {"type": "string"},
                        "size": {"type": "string"},
                        "size.memory": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat PIT segments API."
                },
                "CatPitSegmentsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatPitSegmentRow"},
                    "description": "JSON response emitted by the cat PIT segments API."
                },
                "CatPluginRow": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "name": {"type": "string"},
                        "component": {"type": "string"},
                        "version": {"type": "string"},
                        "opensearch_version": {"type": "string"},
                        "java_version": {"type": "string"},
                        "description": {"type": "string"},
                        "classname": {"type": "string"},
                        "custom_foldername": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat plugins API."
                },
                "CatRecoveryRow": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string"},
                        "shard": {"type": "string"},
                        "start_time": {"type": "string"},
                        "name": {"type": "string"},
                        "time": {"type": "string"},
                        "type": {"type": "string"},
                        "stage": {"type": "string"},
                        "source_host": {"type": "string"},
                        "source_node": {"type": "string"},
                        "target_host": {"type": "string"},
                        "target_node": {"type": "string"},
                        "repository": {"type": "string"},
                        "snapshot": {"type": "string"},
                        "files": {"type": "string"},
                        "files_recovered": {"type": "string"},
                        "files_percent": {"type": "string"},
                        "bytes": {"type": "string"},
                        "bytes_recovered": {"type": "string"},
                        "bytes_percent": {"type": "string"},
                        "translog_ops": {"type": "string"},
                        "translog_ops_recovered": {"type": "string"},
                        "translog_ops_percent": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat recovery API."
                },
                "CatPluginsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatPluginRow"},
                    "description": "JSON response emitted by the cat plugins API."
                },
                "CatRecoveryResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatRecoveryRow"},
                    "description": "JSON response emitted by the cat recovery API."
                },
                "CatRepositoryRow": {
                    "type": "object",
                    "properties": {
                        "id": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat repositories API."
                },
                "CatRepositoriesResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatRepositoryRow"},
                    "description": "JSON response emitted by the cat repositories API."
                },
                "CatSegmentRow": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string"},
                        "shard": {"type": "string"},
                        "prirep": {"type": "string"},
                        "ip": {"type": "string"},
                        "id": {"type": "string"},
                        "segment": {"type": "string"},
                        "generation": {"type": "string"},
                        "docs.count": {"type": "string"},
                        "docs.deleted": {"type": "string"},
                        "size": {"type": "string"},
                        "size.memory": {"type": "string"},
                        "committed": {"type": "string"},
                        "searchable": {"type": "string"},
                        "compound": {"type": "string"},
                        "version": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat segments API."
                },
                "CatSegmentsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatSegmentRow"},
                    "description": "JSON response emitted by the cat segments API."
                },
                "CatShardRow": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "string"},
                        "shard": {"type": "string"},
                        "prirep": {"type": "string"},
                        "state": {"type": "string"},
                        "docs": {"type": "string"},
                        "store": {"type": "string"},
                        "committed": {"type": "string"},
                        "ip": {"type": "string"},
                        "node": {"type": "string"},
                        "sync_id": {"type": "string"},
                        "unassigned.reason": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat shards API."
                },
                "CatShardsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatShardRow"},
                    "description": "JSON response emitted by the cat shards API."
                },
                "CatSnapshotRow": {
                    "type": "object",
                    "properties": {
                        "repository": {"type": "string"},
                        "id": {"type": "string"},
                        "status": {"type": "string"},
                        "start_epoch": {"type": "string"},
                        "start_time": {"type": "string"},
                        "end_epoch": {"type": "string"},
                        "end_time": {"type": "string"},
                        "duration": {"type": "string"},
                        "indices": {"type": "string"},
                        "successful_shards": {"type": "string"},
                        "failed_shards": {"type": "string"},
                        "total_shards": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat snapshots API."
                },
                "CatSnapshotsResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatSnapshotRow"},
                    "description": "JSON response emitted by the cat snapshots API."
                },
                "CatTaskRow": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string"},
                        "type": {"type": "string"},
                        "task_id": {"type": "string"},
                        "parent_task_id": {"type": "string"},
                        "start_time": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "running_time": {"type": "string"},
                        "running_time_ns": {"type": "string"},
                        "cancellable": {"type": "string"},
                        "headers": {"type": "string"},
                        "ip": {"type": "string"},
                        "node": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat tasks API."
                },
                "CatTasksResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatTaskRow"},
                    "description": "JSON response emitted by the cat tasks API."
                },
                "CatTemplateRow": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "index_patterns": {"type": "string"},
                        "order": {"type": "string"},
                        "priority": {"type": "string"},
                        "version": {"type": "string"},
                        "composed_of": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat templates API."
                },
                "CatTemplatesResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatTemplateRow"},
                    "description": "JSON response emitted by the cat templates API."
                },
                "CatThreadPoolRow": {
                    "type": "object",
                    "properties": {
                        "node_name": {"type": "string"},
                        "name": {"type": "string"},
                        "active": {"type": "string"},
                        "size": {"type": "string"},
                        "queue_size": {"type": "string"},
                        "queue": {"type": "string"},
                        "rejected": {"type": "string"},
                        "largest": {"type": "string"},
                        "completed": {"type": "string"},
                        "threads": {"type": "string"},
                        "completed": {"type": "string"},
                    },
                    "additionalProperties": True,
                    "description": "Representative row returned by the cat thread pool API."
                },
                "CatThreadPoolResponse": {
                    "type": "array",
                    "items": {"$ref": "#/components/schemas/CatThreadPoolRow"},
                    "description": "JSON response emitted by the cat thread pool API."
                },
                "OpenSearchErrorCause": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["type", "reason"],
                    "additionalProperties": True,
                },
                "OpenSearchErrorBody": {
                    "type": "object",
                    "properties": {
                        "root_cause": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/OpenSearchErrorCause"},
                        },
                        "type": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["type", "reason"],
                    "additionalProperties": True,
                },
                "OpenSearchErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {"$ref": "#/components/schemas/OpenSearchErrorBody"},
                        "status": {"type": "integer"},
                    },
                    "required": ["error", "status"],
                    "additionalProperties": True,
                },
            }
        },
        "paths": {},
    }
    paths: dict[str, dict] = {}
    for row in rows:
        method = row["method"].lower()
        path = normalize_openapi_path(row["path_or_expression"])
        if method not in {"get", "put", "post", "delete", "head"}:
            continue
        if path is None:
            continue
        if not include_openapi_operation(row, path, method):
            continue
        family = rest_family(row)
        profile, entrypoint = rest_evidence_owner(row)
        path_item = paths.setdefault(path, {})
        path_item[method] = {
            "summary": rest_meaning(row["method"], path, row["source"]),
            "description": rest_gap(row["status"], family, path),
            "operationId": operation_id(method, path),
            "tags": [family],
            "parameters": path_parameters(path) + query_parameters(path, method),
            "responses": responses_for(path, method),
            "x-steelsearch-status": row["status"],
            "x-steelsearch-family": family,
            "x-evidence-profile": profile,
            "x-evidence-entrypoint": entrypoint,
            "x-opensearch-source": row["source"],
            "x-opensearch-source-line": row["line"],
        }
        request_body = request_body_for(path, method)
        if request_body is not None:
            path_item[method]["requestBody"] = request_body
    spec["paths"] = dict(sorted(paths.items()))
    return spec


def main() -> None:
    rest_rows = apply_runtime_route_status([row for row in read_tsv(REST_TSV) if include_rest_row(row)])
    transport_rows = read_tsv(TRANSPORT_TSV)
    write_text(OUT_DIR / "rest-routes.md", render_rest_reference(rest_rows))
    write_text(OUT_DIR / "transport-actions.md", render_transport_reference(transport_rows))
    write_text(OUT_DIR / "route-evidence-matrix.md", render_route_evidence_matrix(rest_rows))
    write_text(
        OUT_DIR / "openapi.json",
        json.dumps(generate_openapi(rest_rows), indent=2, sort_keys=True) + "\n",
    )


if __name__ == "__main__":
    main()
