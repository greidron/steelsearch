#!/usr/bin/env python3
"""Check runtime-control inventory matches current thread-pool evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "docs/rust-port/current-runtime-control-surface-inventory.md"
SOURCE_ROUTES = ROOT / "docs/rust-port/generated/source-rest-routes.tsv"
RUNTIME_LEDGER = ROOT / "docs/api-spec/generated/runtime-route-ledger.json"
RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"
ROOT_CAT_FIXTURE = ROOT / "tools/fixtures/root-cluster-node-cat-compat.json"
SEARCH_FIXTURE = ROOT / "tools/fixtures/search-compat.json"

REQUIRED_DOC_TOKENS = [
    "GET /_cat/thread_pool",
    "GET /_cat/thread_pool/{thread_pool_patterns}",
    "implemented standalone inspection surface",
    "runtime_thread_pool_counters",
    "production scheduler equivalence",
]

FORBIDDEN_DOC_TOKENS = [
    "no first-class route inventoried in current standalone runtime evidence",
    "no authoritative runtime surface",
    "if thread-pool routes remain absent",
]

REQUIRED_SOURCE_ROUTE_TOKENS = [
    "GET\t/_cat/thread_pool\t",
    "GET\t/_cat/thread_pool/{thread_pool_patterns}\t",
]

REQUIRED_RUNTIME_LEDGER_TOKENS = [
    '"/_cat/thread_pool"',
    '"/_cat/thread_pool/search"',
]

REQUIRED_RUNTIME_SOURCE_TOKENS = [
    "fn handle_cat_thread_pool_route",
    'self.runtime_thread_pool_counters("search")',
    'self.remote_transport_thread_pool_counters(&node_id)',
    "fn cat_thread_pool_routes_serve_json_text_and_target_filters",
    "fn cat_thread_pool_keeps_opensearch_node_then_pool_order",
]

REQUIRED_FIXTURE_TOKENS = [
    "cat_thread_pool_text",
    "cat_thread_pool_target_text",
    "cat_thread_pool_root_json",
    "cat_thread_pool_json_selected_alias_columns",
]


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def missing_tokens(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token not in text]


def present_tokens(text: str, tokens: list[str]) -> list[str]:
    return [token for token in tokens if token in text]


def main() -> int:
    doc = read(DOC)
    source_routes = read(SOURCE_ROUTES)
    runtime_ledger = read(RUNTIME_LEDGER)
    runtime_source = read(RUNTIME_SOURCE)
    fixtures = "\n".join([read(ROOT_CAT_FIXTURE), read(SEARCH_FIXTURE)])

    errors: list[str] = []
    checks = {
        "doc_required": missing_tokens(doc, REQUIRED_DOC_TOKENS),
        "doc_forbidden": present_tokens(doc, FORBIDDEN_DOC_TOKENS),
        "source_routes": missing_tokens(source_routes, REQUIRED_SOURCE_ROUTE_TOKENS),
        "runtime_ledger": missing_tokens(runtime_ledger, REQUIRED_RUNTIME_LEDGER_TOKENS),
        "runtime_source": missing_tokens(runtime_source, REQUIRED_RUNTIME_SOURCE_TOKENS),
        "fixtures": missing_tokens(fixtures, REQUIRED_FIXTURE_TOKENS),
    }
    for name, failures in checks.items():
        if failures:
            errors.append(f"{name}: {failures}")

    result = {
        "status": "ok" if not errors else "failed",
        "errors": errors,
        "summary": {
            "doc_required_token_count": len(REQUIRED_DOC_TOKENS),
            "doc_forbidden_token_count": len(FORBIDDEN_DOC_TOKENS),
            "source_route_token_count": len(REQUIRED_SOURCE_ROUTE_TOKENS),
            "runtime_ledger_token_count": len(REQUIRED_RUNTIME_LEDGER_TOKENS),
            "runtime_source_token_count": len(REQUIRED_RUNTIME_SOURCE_TOKENS),
            "fixture_token_count": len(REQUIRED_FIXTURE_TOKENS),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
