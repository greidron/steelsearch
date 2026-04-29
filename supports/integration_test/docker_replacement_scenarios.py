#!/usr/bin/env python3
"""Docker-based OpenSearch replacement smoke and migration scenarios."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


DOCS = [
    {"_id": "1", "_source": {"tenant": "alpha", "title": "fresh apple", "price": 10}},
    {"_id": "2", "_source": {"tenant": "alpha", "title": "green apple", "price": 12}},
    {"_id": "3", "_source": {"tenant": "beta", "title": "blue car", "price": 30}},
]


@dataclass
class Scenario:
    name: str
    status: str = "pending"
    details: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class HttpJson:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url.rstrip("/")

    def request(
        self,
        method: str,
        path: str,
        body: Any | None = None,
        expected: set[int] | None = None,
    ) -> tuple[int, Any]:
        expected = expected or {200}
        payload = None if body is None else json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            data = {"raw": text}
        if status not in expected:
            raise AssertionError(f"{method} {path} returned {status}: {data}")
        return status, data

    def request_raw(
        self,
        method: str,
        path: str,
        payload: bytes,
        content_type: str,
        expected: set[int] | None = None,
    ) -> tuple[int, Any]:
        expected = expected or {200}
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=payload,
            method=method,
            headers={"Content-Type": content_type},
        )
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                status = response.status
                raw = response.read()
        except urllib.error.HTTPError as error:
            status = error.code
            raw = error.read()
        text = raw.decode("utf-8", errors="replace")
        try:
            data = json.loads(text) if text else {}
        except json.JSONDecodeError:
            data = {"raw": text}
        if status not in expected:
            raise AssertionError(f"{method} {path} returned {status}: {data}")
        return status, data


def hit_ids(response: dict[str, Any]) -> list[str]:
    return [hit["_id"] for hit in response["hits"]["hits"]]


def checksum_docs(docs: list[dict[str, Any]]) -> str:
    normalized = [
        {"_id": doc["_id"], "_source": doc["_source"]}
        for doc in sorted(docs, key=lambda item: item["_id"])
    ]
    payload = json.dumps(normalized, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_text_index(client: HttpJson, index: str) -> None:
    client.request(
        "PUT",
        f"/{index}",
        {
            "settings": {"number_of_shards": 1, "number_of_replicas": 0},
            "mappings": {
                "properties": {
                    "tenant": {"type": "keyword"},
                    "title": {"type": "text"},
                    "price": {"type": "long"},
                }
            },
        },
        expected={200, 201},
    )


def index_docs(client: HttpJson, index: str, docs: list[dict[str, Any]]) -> None:
    for doc in docs:
        client.request("PUT", f"/{index}/_doc/{doc['_id']}", doc["_source"], expected={200, 201})
    client.request("POST", f"/{index}/_refresh", expected={200})


def bulk_index_docs(client: HttpJson, index: str, docs: list[dict[str, Any]]) -> dict[str, Any]:
    lines: list[str] = []
    for doc in docs:
        lines.append(json.dumps({"index": {"_index": index, "_id": doc["_id"]}}, separators=(",", ":")))
        lines.append(json.dumps(doc["_source"], separators=(",", ":")))
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    _, response = client.request_raw(
        "POST",
        "/_bulk",
        payload,
        "application/x-ndjson",
        expected={200},
    )
    if response.get("errors"):
        raise AssertionError(f"bulk import returned item errors: {response}")
    client.request("POST", f"/{index}/_refresh", expected={200})
    return response


def search_ids(client: HttpJson, index: str, query: dict[str, Any]) -> list[str]:
    _, response = client.request("POST", f"/{index}/_search", query)
    return sorted(hit_ids(response))


def cleanup(client: HttpJson, *indices: str) -> None:
    for index in indices:
        try:
            client.request("DELETE", f"/{index}", expected={200, 202, 404})
        except Exception:
            pass


def scenario_root_and_health(opensearch: HttpJson, steelsearch: HttpJson) -> Scenario:
    scenario = Scenario("root_and_health")
    os_root = opensearch.request("GET", "/")[1]
    ss_root = steelsearch.request("GET", "/")[1]
    os_health = opensearch.request("GET", "/_cluster/health")[1]
    ss_health = steelsearch.request("GET", "/_cluster/health")[1]
    scenario.status = "passed"
    scenario.details = {
        "opensearch": {"version": os_root.get("version"), "health": os_health.get("status")},
        "steelsearch": {"version": ss_root.get("version"), "health": ss_health.get("status")},
    }
    return scenario


def scenario_search_compare(opensearch: HttpJson, steelsearch: HttpJson, suffix: str) -> Scenario:
    scenario = Scenario("search_compare")
    index = f"docker-compare-{suffix}"
    cleanup(opensearch, index)
    cleanup(steelsearch, index)
    try:
        create_text_index(opensearch, index)
        create_text_index(steelsearch, index)
        index_docs(opensearch, index, DOCS)
        index_docs(steelsearch, index, DOCS)

        queries = {
            "match_all": {"query": {"match_all": {}}},
            "match_title": {"query": {"match": {"title": "apple"}}},
            "term_tenant": {"query": {"term": {"tenant": "alpha"}}},
            "range_price": {"query": {"range": {"price": {"gte": 11}}}},
        }
        comparisons = {}
        for name, query in queries.items():
            os_ids = search_ids(opensearch, index, query)
            ss_ids = search_ids(steelsearch, index, query)
            comparisons[name] = {"opensearch": os_ids, "steelsearch": ss_ids}
            if os_ids != ss_ids:
                raise AssertionError(f"{name} mismatch: {comparisons[name]}")
        scenario.status = "passed"
        scenario.details = {"index": index, "comparisons": comparisons}
        return scenario
    finally:
        cleanup(opensearch, index)
        cleanup(steelsearch, index)


def scenario_migration(opensearch: HttpJson, steelsearch: HttpJson, suffix: str) -> Scenario:
    scenario = Scenario("opensearch_to_steelsearch_migration")
    source = f"docker-migrate-source-{suffix}"
    target = f"docker-migrate-target-{suffix}"
    cleanup(opensearch, source)
    cleanup(steelsearch, target)
    try:
        create_text_index(opensearch, source)
        index_docs(opensearch, source, DOCS)
        _, exported = opensearch.request(
            "POST",
            f"/{source}/_search",
            {"size": 100, "query": {"match_all": {}}},
        )
        exported_docs = [
            {"_id": hit["_id"], "_source": hit["_source"]}
            for hit in exported["hits"]["hits"]
        ]

        create_text_index(steelsearch, target)
        bulk_response = bulk_index_docs(steelsearch, target, exported_docs)
        _, imported = steelsearch.request(
            "POST",
            f"/{target}/_search",
            {"size": 100, "query": {"match_all": {}}},
        )
        imported_docs = [
            {"_id": hit["_id"], "_source": hit["_source"]}
            for hit in imported["hits"]["hits"]
        ]
        source_checksum = checksum_docs(exported_docs)
        target_checksum = checksum_docs(imported_docs)
        if source_checksum != target_checksum:
            raise AssertionError(
                f"migration checksum mismatch: {source_checksum} != {target_checksum}"
            )
        scenario.status = "passed"
        scenario.details = {
            "source_index": source,
            "target_index": target,
            "import_api": "_bulk",
            "bulk_items": len(bulk_response.get("items", [])),
            "document_count": len(imported_docs),
            "checksum": target_checksum,
        }
        return scenario
    finally:
        cleanup(opensearch, source)
        cleanup(steelsearch, target)


def predict_vector(steelsearch: HttpJson, model_id: str, text: str) -> list[float]:
    _, response = steelsearch.request(
        "POST",
        f"/_plugins/_ml/models/{model_id}/_predict",
        {"model_id": model_id, "texts": [text]},
    )
    return response["vectors"][0]


def scenario_steelsearch_knn_minilm(steelsearch: HttpJson, suffix: str) -> Scenario:
    scenario = Scenario("steelsearch_knn_minilm")
    index = f"docker-knn-{suffix}"
    model_id = f"minilm-onnx-{suffix}"
    cleanup(steelsearch, index)
    try:
        steelsearch.request(
            "POST",
            "/_plugins/_ml/model_groups/_register",
            {
                "group_id": f"group-{suffix}",
                "name": f"embeddings-{suffix}",
                "access": {
                    "owner": "steelsearch-dev",
                    "backend_roles": ["ml-admin"],
                    "tenant": "development",
                    "is_public": False,
                },
            },
            expected={200, 400},
        )
        steelsearch.request(
            "POST",
            "/_plugins/_ml/models/_register",
            {
                "model_id": model_id,
                "group_id": f"group-{suffix}",
                "name": "all-MiniLM-L6-v2",
                "version": "1",
                "format": "onnx",
                "inference": {
                    "kind": "text_embedding",
                    "embedding_dimension": 8,
                    "max_sequence_length": 16,
                    "normalize": True,
                    "pooling": "mean",
                },
            },
            expected={200, 400},
        )
        steelsearch.request(
            "POST",
            f"/_plugins/_ml/models/{model_id}/_deploy",
            expected={200, 400},
        )

        docs = [
            {"_id": "a", "text": "steelsearch vector search", "tenant": "alpha"},
            {"_id": "b", "text": "opensearch migration test", "tenant": "alpha"},
            {"_id": "c", "text": "blue sports car", "tenant": "beta"},
        ]
        steelsearch.request(
            "PUT",
            f"/{index}",
            {
                "settings": {"index": {"knn": True}, "number_of_shards": 1, "number_of_replicas": 0},
                "mappings": {
                    "properties": {
                        "tenant": {"type": "keyword"},
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 8,
                            "method": {"name": "hnsw", "engine": "lucene", "space_type": "l2"},
                        },
                    }
                },
            },
            expected={200, 201},
        )
        steelsearch.request("GET", f"/{index}", expected={200})
        for doc in docs:
            vector = predict_vector(steelsearch, model_id, doc["text"])
            steelsearch.request(
                "PUT",
                f"/{index}/_doc/{doc['_id']}",
                {"tenant": doc["tenant"], "text": doc["text"], "embedding": vector},
                expected={200, 201},
            )
        steelsearch.request("POST", f"/{index}/_refresh")
        query_vector = predict_vector(steelsearch, model_id, "vector search with steelsearch")
        _, response = steelsearch.request(
            "POST",
            f"/{index}/_search",
            {"query": {"knn": {"embedding": {"vector": query_vector, "k": 2}}}},
        )
        ids = hit_ids(response)
        if not ids:
            raise AssertionError("k-NN query returned no hits")
        scenario.status = "passed"
        scenario.details = {"index": index, "hit_ids": ids, "vector_dimension": len(query_vector)}
        return scenario
    finally:
        cleanup(steelsearch, index)


def run_required(name: str, fn: Any, scenarios: list[Scenario]) -> None:
    try:
        scenarios.append(fn())
    except Exception as error:
        scenarios.append(Scenario(name, status="failed", error=str(error)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--steelsearch-url", required=True)
    parser.add_argument("--opensearch-url", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    opensearch = HttpJson(args.opensearch_url)
    steelsearch = HttpJson(args.steelsearch_url)
    suffix = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    scenarios: list[Scenario] = []

    run_required("root_and_health", lambda: scenario_root_and_health(opensearch, steelsearch), scenarios)
    run_required("search_compare", lambda: scenario_search_compare(opensearch, steelsearch, suffix), scenarios)
    run_required(
        "opensearch_to_steelsearch_migration",
        lambda: scenario_migration(opensearch, steelsearch, suffix),
        scenarios,
    )
    run_required(
        "steelsearch_knn_minilm",
        lambda: scenario_steelsearch_knn_minilm(steelsearch, suffix),
        scenarios,
    )

    report = {
        "opensearch_url": args.opensearch_url,
        "steelsearch_url": args.steelsearch_url,
        "scenarios": [scenario.__dict__ for scenario in scenarios],
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    failures = [scenario for scenario in scenarios if scenario.status != "passed"]
    if failures:
        print(json.dumps(report, indent=2, sort_keys=True))
        return 1
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
