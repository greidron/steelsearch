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
DEV_CLUSTER_TESTS = ROOT / "crates/os-node/tests/dev_cluster_daemons.rs"
NATIVE_CLOSURE_RUNNER = ROOT / "tools/run-native-closure-validation.py"
NATIVE_CLOSURE_STATUS = ROOT / "tools/check-native-closure-status-report.py"
ROOT_CAT_FIXTURE = ROOT / "tools/fixtures/root-cluster-node-cat-compat.json"
SEARCH_FIXTURE = ROOT / "tools/fixtures/search-compat.json"
SEARCH_PROMOTION_GATE = ROOT / "tools/fixtures/search-promotion-gate.json"
ALL_PROMOTION_GATES = ROOT / "tools/check-all-promotion-gates.py"

REQUIRED_DOC_TOKENS = [
    "GET /_cat/thread_pool",
    "GET /_cat/thread_pool/{thread_pool_patterns}",
    "implemented standalone inspection surface",
    "runtime_thread_pool_counters",
    "production scheduler equivalence",
    "PIT runtime evidence",
    "check-pit-e2e-coverage.py",
    "comparison cases to stay present",
    "runtime-fairness",
    "13/13 bounded fairness tests",
    "remote-backlog admission isolation",
]

FORBIDDEN_DOC_TOKENS = [
    "no first-class route inventoried in current standalone runtime evidence",
    "does not yet claim a first-class thread-pool API family",
    "no authoritative runtime surface",
    "if thread-pool routes remain absent",
    "live multi-node fairness contracts are still missing",
    "there is no evidence for task class prioritisation",
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

REQUIRED_DEV_CLUSTER_TEST_TOKENS = [
    "daemon_point_in_time_search_preserves_snapshot_over_real_socket",
    "daemon_point_in_time_contexts_do_not_survive_restart",
    "multi_daemon_transport_create_pit_binds_reader_contexts_to_target_node",
]

REQUIRED_SEARCH_GATE_TOKENS = [
    "pit_snapshot_after_update_delete_search",
    "pit_search_after_close_missing_context",
    "msearch_pit_snapshot_after_update_delete_search",
]

REQUIRED_ALL_GATE_TOKENS = [
    "pit-e2e-coverage",
    "tools/check-pit-e2e-coverage.py",
    "--require-all-pit-passed",
]

REQUIRED_NATIVE_CLOSURE_TOKENS = [
    '"runtime-fairness"',
    "runtime-fairness-remote-transport-backpressure",
    "live_multi_daemon_query_phase_transport_queue_rejection_is_reported_in_rest_telemetry",
]

REQUIRED_NATIVE_STATUS_TOKENS = [
    '"runtime-fairness": 13',
    "runtime_control_batches_have_no_queue_backpressure_fairness_or_lifecycle_regressions",
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
    dev_cluster_tests = read(DEV_CLUSTER_TESTS)
    native_closure_runner = read(NATIVE_CLOSURE_RUNNER)
    native_closure_status = read(NATIVE_CLOSURE_STATUS)
    fixtures = "\n".join([read(ROOT_CAT_FIXTURE), read(SEARCH_FIXTURE)])
    search_promotion_gate = read(SEARCH_PROMOTION_GATE)
    all_promotion_gates = read(ALL_PROMOTION_GATES)

    errors: list[str] = []
    checks = {
        "doc_required": missing_tokens(doc, REQUIRED_DOC_TOKENS),
        "doc_forbidden": present_tokens(doc, FORBIDDEN_DOC_TOKENS),
        "source_routes": missing_tokens(source_routes, REQUIRED_SOURCE_ROUTE_TOKENS),
        "runtime_ledger": missing_tokens(runtime_ledger, REQUIRED_RUNTIME_LEDGER_TOKENS),
        "runtime_source": missing_tokens(runtime_source, REQUIRED_RUNTIME_SOURCE_TOKENS),
        "fixtures": missing_tokens(fixtures, REQUIRED_FIXTURE_TOKENS),
        "dev_cluster_tests": missing_tokens(
            dev_cluster_tests,
            REQUIRED_DEV_CLUSTER_TEST_TOKENS,
        ),
        "search_promotion_gate": missing_tokens(
            search_promotion_gate,
            REQUIRED_SEARCH_GATE_TOKENS,
        ),
        "all_promotion_gates": missing_tokens(
            all_promotion_gates,
            REQUIRED_ALL_GATE_TOKENS,
        ),
        "native_closure_runner": missing_tokens(
            native_closure_runner,
            REQUIRED_NATIVE_CLOSURE_TOKENS,
        ),
        "native_closure_status": missing_tokens(
            native_closure_status,
            REQUIRED_NATIVE_STATUS_TOKENS,
        ),
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
            "dev_cluster_test_token_count": len(REQUIRED_DEV_CLUSTER_TEST_TOKENS),
            "search_gate_token_count": len(REQUIRED_SEARCH_GATE_TOKENS),
            "all_gate_token_count": len(REQUIRED_ALL_GATE_TOKENS),
            "native_closure_runner_token_count": len(REQUIRED_NATIVE_CLOSURE_TOKENS),
            "native_closure_status_token_count": len(REQUIRED_NATIVE_STATUS_TOKENS),
        },
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
