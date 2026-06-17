import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX_PATH = ROOT / "tools" / "run-search-benchmark-matrix.py"
BASELINE_PATH = ROOT / "tools" / "run-http-load-baseline.py"

EXPECTED_NATIVE_COUNTERS = (
    "materialized_response_fetches",
    "materialized_response_avoided_fetches",
    "compatibility_materialized_response_fetches",
    "request_result_cache_hybrid_vector_bypasses",
    "request_result_cache_unsupported_vector_bypasses",
    "request_result_cache_highlight_bypasses",
    "request_result_cache_explain_bypasses",
)


def load_matrix_module():
    module_name = "run_search_benchmark_matrix"
    spec = importlib.util.spec_from_file_location(module_name, MATRIX_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class BenchmarkTelemetryScriptTests(unittest.TestCase):
    def test_http_load_baseline_dry_run_exposes_all_native_telemetry_counters(self):
        result = subprocess.run(
            [
                sys.executable,
                str(BASELINE_PATH),
                "--dry-run",
                "--duration-seconds",
                "1",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertFalse(payload["config"]["operation_resource_deltas"])
        resource_usage = payload["resource_usage"]
        for counter in EXPECTED_NATIVE_COUNTERS:
            self.assertEqual(resource_usage[counter]["source"], "/_nodes/stats")
        self.assertNotIn(
            "fallback_query_string",
            [operation["operation"] for operation in payload["operations"]],
        )

    def test_http_load_baseline_dry_run_exposes_opt_in_fallback_operation(self):
        result = subprocess.run(
            [
                sys.executable,
                str(BASELINE_PATH),
                "--dry-run",
                "--duration-seconds",
                "1",
                "--query-mix",
                "fallback_query_string=1",
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            payload["operations"],
            [{"operation": "fallback_query_string", "weight": 1, "share": 1.0}],
        )

    def test_benchmark_matrix_report_exposes_all_native_telemetry_counters(self):
        matrix = load_matrix_module()
        result = {
            "generated_at_epoch_seconds": 0,
            "config": {
                "profile": "test",
                "corpus_size": 1,
                "vector_dimension": 2,
                "duration_seconds": 1.0,
                "clients": 1,
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "query_mix": "lexical=1",
                "seed": 13,
            },
            "scenarios": {
                "steelsearch-single-node": {
                    "base_url": "http://127.0.0.1:9200",
                    "manifest_path": None,
                    "summary": {
                        "throughput_ops_per_second": 1.0,
                        "error_rate": 0.0,
                    },
                    "resource_usage": {
                        counter: {"delta": index, "after": index + 10}
                        for index, counter in enumerate(EXPECTED_NATIVE_COUNTERS, start=1)
                    },
                    "operations": {
                        "lexical": {
                            "success_count": 4,
                            "error_count": 0,
                            "latency_ms": {
                                "p50": 1.0,
                                "p95": 1.0,
                                "p99": 1.0,
                                "mean": 1.0,
                            },
                            "resource_usage": {
                                "materialized_response_fetches": {"delta": 1},
                                "compatibility_materialized_response_fetches": {"delta": 0},
                            },
                        }
                    },
                }
            },
            "comparisons": {},
        }

        report = matrix.render_report(result)

        self.assertIn("### Steelsearch native-path telemetry", report)
        for counter in EXPECTED_NATIVE_COUNTERS:
            self.assertIn(f"| `{counter}` |", report)
        self.assertIn("### Steelsearch materialization budget", report)
        self.assertIn("| `materialized_response_fetches` | 1 | 4 | 0.25 | 1.00 | `pass` |", report)
        self.assertIn(
            "| `compatibility_materialized_response_fetches` | 3 | 4 | 0.75 | 1.00 | `pass` |",
            report,
        )
        self.assertIn("### Steelsearch operation materialization budget", report)
        self.assertIn(
            "| lexical | `materialized_response_fetches` | 1 | 4 | 0.25 | 1.00 | `pass` |",
            report,
        )
        self.assertIn("`fallback_query_string`: opt-in diagnostic query-string fallback case", report)

    def test_benchmark_matrix_json_marks_materialization_budget_failures(self):
        matrix = load_matrix_module()
        budgets = matrix.build_native_telemetry_budgets(
            {
                "steelsearch-single-node": {
                    "resource_usage": {
                        "materialized_response_fetches": {"delta": 5},
                        "compatibility_materialized_response_fetches": {"delta": 1},
                    },
                    "operations": {
                        "lexical": {"success_count": 2},
                    },
                }
            }
        )

        scenario = budgets["steelsearch-single-node"]
        self.assertEqual(scenario["status"], "fail")
        self.assertEqual(
            scenario["counters"]["materialized_response_fetches"]["status"],
            "fail",
        )
        self.assertEqual(
            scenario["counters"]["compatibility_materialized_response_fetches"]["status"],
            "pass",
        )

    def test_benchmark_matrix_json_marks_operation_materialization_budget_failures(self):
        matrix = load_matrix_module()
        budgets = matrix.build_native_telemetry_budgets(
            {
                "steelsearch-single-node": {
                    "resource_usage": {
                        "materialized_response_fetches": {"delta": 5},
                        "compatibility_materialized_response_fetches": {"delta": 1},
                    },
                    "operations": {
                        "facet": {
                            "success_count": 2,
                            "resource_usage": {
                                "materialized_response_fetches": {"delta": 4},
                                "compatibility_materialized_response_fetches": {"delta": 0},
                            },
                        },
                        "lexical": {
                            "success_count": 3,
                            "resource_usage": {
                                "materialized_response_fetches": {"delta": 1},
                                "compatibility_materialized_response_fetches": {"delta": 1},
                            },
                        },
                    },
                }
            }
        )

        operations = budgets["steelsearch-single-node"]["operations"]
        self.assertEqual(operations["facet"]["status"], "fail")
        self.assertEqual(
            operations["facet"]["counters"]["materialized_response_fetches"]["per_success"],
            2.0,
        )
        self.assertEqual(operations["lexical"]["status"], "pass")


if __name__ == "__main__":
    unittest.main()
