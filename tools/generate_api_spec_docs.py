#!/usr/bin/env python3
from __future__ import annotations

import csv
from collections import defaultdict
import json
from pathlib import Path


ROOT = Path("/home/ubuntu/steelsearch")
REST_TSV = ROOT / "docs/rust-port/generated/source-rest-routes.tsv"
TRANSPORT_TSV = ROOT / "docs/rust-port/generated/source-transport-actions.tsv"
OUT_DIR = ROOT / "docs/api-spec/generated"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open() as f:
        return list(csv.DictReader(f, delimiter="\t"))


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


def literal_openapi_path(path: str) -> bool:
    return (
        path.startswith("/")
        and '"' not in path
        and " " not in path
        and "+" not in path
        and "(" not in path
        and ")" not in path
    )


def generate_openapi(rows: list[dict[str, str]]) -> dict:
    spec: dict[str, object] = {
        "openapi": "3.0.3",
        "info": {
            "title": "Steelsearch OpenSearch-Compatible API",
            "version": "0.1.0",
            "description": (
                "Generated OpenAPI companion built from the source-derived REST route "
                "inventory. This reflects route inventory and evidence ownership, not "
                "a claim that every listed route is fully implemented."
            ),
        },
        "servers": [{"url": "/"}],
        "paths": {},
    }
    paths: dict[str, dict] = {}
    for row in rows:
        method = row["method"].lower()
        path = row["path_or_expression"]
        if method not in {"get", "put", "post", "delete", "head"}:
            continue
        if not literal_openapi_path(path):
            continue
        family = rest_family(row)
        profile, entrypoint = rest_evidence_owner(row)
        path_item = paths.setdefault(path, {})
        path_item[method] = {
            "summary": rest_meaning(row["method"], path, row["source"]),
            "description": rest_gap(row["status"], family, path),
            "tags": [family],
            "responses": {
                "200": {"description": "Successful response envelope"},
                "400": {"description": "OpenSearch-shaped fail-closed error"},
                "404": {"description": "Not found"},
            },
            "x-steelsearch-status": row["status"],
            "x-steelsearch-family": family,
            "x-evidence-profile": profile,
            "x-evidence-entrypoint": entrypoint,
            "x-opensearch-source": row["source"],
            "x-opensearch-source-line": row["line"],
        }
    spec["paths"] = dict(sorted(paths.items()))
    return spec


def main() -> None:
    rest_rows = read_tsv(REST_TSV)
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
