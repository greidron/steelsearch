#!/usr/bin/env python3
"""Generate a current-reference replacement for the missing bool-minimum fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "tools" / "fixtures" / "search-bool-minimum-replacement-compat.json"
MISSING_INPUT = "target/core-replacement-c05/bool-minimum-compat.json"

DOCUMENTS = [
    {"_id": "all", "_source": {"title": "alpha", "tags": ["alpha", "beta", "gamma"], "value": 0}},
    {"_id": "pair", "_source": {"title": "alpha", "tags": ["alpha", "beta"], "value": 1}},
    {"_id": "single", "_source": {"title": "alpha", "tags": ["alpha"], "value": 2}},
    {"_id": "none", "_source": {"title": "alpha", "tags": [], "value": 3}},
    {"_id": "blocked", "_source": {"title": "alpha", "tags": ["alpha", "beta", "gamma"], "blocked": True, "value": 4}},
]


def query(minimum_should_match: int, exclude_blocked: bool) -> dict:
    clauses: dict = {
        "must": [{"match_all": {}}],
        "should": [{"term": {"tags": tag}} for tag in ("alpha", "beta", "gamma")],
        "minimum_should_match": minimum_should_match,
    }
    if exclude_blocked:
        clauses["must_not"] = [{"term": {"blocked": True}}]
    return {"bool": clauses}


def search_body(current_query: dict) -> dict:
    return {"size": 10, "track_total_hits": True, "query": current_query}


def aggregation_body(current_query: dict) -> dict:
    return {
        "size": 0,
        "track_total_hits": True,
        "query": current_query,
        "aggs": {"matched_values": {"value_count": {"field": "value"}}},
    }


def build_fixture() -> dict:
    indices = []
    bulk = []
    cases = []
    for shard_count in (1, 3):
        index = f"bool-minimum-replacement-{shard_count}"
        indices.append(
            {
                "name": index,
                "body": {
                    "settings": {
                        "number_of_shards": shard_count,
                        "number_of_replicas": 0,
                        "refresh_interval": "-1",
                    },
                    "mappings": {
                        "properties": {
                            "title": {"type": "text"},
                            "tags": {"type": "keyword"},
                            "blocked": {"type": "boolean"},
                            "value": {"type": "long"},
                        }
                    },
                },
            }
        )
        bulk.append({"index": index, "documents": DOCUMENTS})
        for minimum_should_match in range(5):
            for exclude_blocked in (False, True):
                variant = "excluded" if exclude_blocked else "included"
                current_query = query(minimum_should_match, exclude_blocked)
                cases.append(
                    {
                        "name": f"{shard_count}-minimum-{minimum_should_match}-{variant}",
                        "area": "search",
                        "family": "bool-minimum-replacement",
                        "extract": "search_scores",
                        "steps": [
                            {
                                "name": "search",
                                "method": "POST",
                                "path": f"/{index}/_search",
                                "expected_status": 200,
                                "body": search_body(current_query),
                                "extract": "search_scores",
                            },
                            {
                                "name": "count",
                                "method": "POST",
                                "path": f"/{index}/_count",
                                "expected_status": 200,
                                "body": {"query": current_query},
                                "extract": "count_query",
                            },
                            {
                                "name": "value-count",
                                "method": "POST",
                                "path": f"/{index}/_search",
                                "expected_status": 200,
                                "body": aggregation_body(current_query),
                                "extract": "aggregations",
                            },
                        ],
                    }
                )
    return {
        "provenance": {
            "kind": "current-reference-replacement",
            "missing_immutable_input": MISSING_INPUT,
            "scope": "minimum_should_match numeric boundaries, exclusion, shard count, and result contracts",
            "not_historical_recovery": True,
        },
        "indices": indices,
        "bulk": bulk,
        "cases": cases,
    }


def rendered_fixture() -> str:
    return json.dumps(build_fixture(), indent=2) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail if the generated fixture is stale")
    args = parser.parse_args()
    rendered = rendered_fixture()
    if args.check:
        return 0 if OUTPUT.exists() and OUTPUT.read_text(encoding="utf-8") == rendered else 1
    OUTPUT.write_text(rendered, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
