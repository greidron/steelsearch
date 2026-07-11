import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import promotion_report_evidence


class PromotionReportEvidenceTests(unittest.TestCase):
    def write_report(self, temp_dir: Path, cases: list[dict]) -> Path:
        report = temp_dir / "report.json"
        report.write_text(json.dumps({"cases": cases}), encoding="utf-8")
        return report

    def test_validate_report_evidence_accepts_passed_cases_and_metadata_evidence(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [
                    {
                        "name": "case-a",
                        "status": "passed",
                        "metadata": {"evidence_classes": ["class-a"]},
                    },
                    {
                        "name": "case-b",
                        "status": "strict_equal",
                        "evidence_class": "class-b",
                    },
                ],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a", "case-b"},
                {"class-a", "class-b"},
            )

            self.assertEqual(errors, [])

    def test_validate_report_evidence_reports_missing_required_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [{"name": "case-a", "status": "passed"}],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a", "case-b"},
                set(),
            )

            self.assertEqual(errors, ["report evidence missing required cases: ['case-b']"])

    def test_validate_report_evidence_reports_non_passed_required_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [{"name": "case-a", "status": "failed"}],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a"},
                set(),
            )

            self.assertEqual(errors, ["report evidence has non-passed required cases: ['case-a']"])

    def test_validate_report_evidence_reports_missing_evidence_classes(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [{"name": "case-a", "status": "passed", "metadata": {"evidence_class": "class-a"}}],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a"},
                {"class-a", "class-b"},
            )

            self.assertEqual(errors, ["report evidence missing required evidence classes: ['class-b']"])

    def test_validate_report_evidence_accepts_required_case_extracts(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [
                    {
                        "name": "case-a",
                        "status": "passed",
                        "steelsearch": {"status": 200, "ids": ["doc-1"], "total": 1},
                    },
                    {
                        "name": "case-b",
                        "status": "passed",
                        "targets": {
                            "steelsearch": {
                                "extract": {"status": 200, "nodes_present": True},
                            },
                        },
                    },
                ],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a", "case-b"},
                set(),
                {
                    "case-a": {"status": 200, "ids": ["doc-1"]},
                    "case-b": {"status": 200, "nodes_present": True},
                },
            )

            self.assertEqual(errors, [])

    def test_validate_report_evidence_reports_missing_required_case_extracts(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            report = self.write_report(
                Path(temp_dir_value),
                [
                    {
                        "name": "case-a",
                        "status": "passed",
                        "steelsearch": {"status": 200, "ids": []},
                    },
                ],
            )

            errors = promotion_report_evidence.validate_report_evidence(
                [report],
                {"case-a"},
                set(),
                {"case-a": {"status": 200, "ids": ["doc-1"]}},
            )

            self.assertEqual(errors, ["report evidence missing required case extracts: ['case-a']"])

    def test_vector_fixture_carries_report_bound_query_cases(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "vector-search-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        for case_name in [
            "knn_search",
            "knn_cosinesimil_search",
            "knn_innerproduct_search",
            "knn_query_happy_path",
            "knn_query_filter_happy_path",
            "knn_query_ignore_unmapped_happy_path",
            "knn_query_radial_max_distance_happy_path",
            "knn_query_method_parameters_happy_path",
            "knn_byte_vector_subset_happy_path",
            "knn_binary_vector_subset_happy_path",
            "knn_nested_filtered_happy_path",
            "hybrid_query_happy_path",
            "hybrid_should_query_happy_path",
            "hybrid_minimum_should_match_happy_path",
        ]:
            self.assertIn(case_name, cases)

        observed_evidence = set()
        for case in cases.values():
            observed_evidence.update((case.get("metadata") or {}).get("evidence_classes") or [])
        self.assertIn("lucene-score-space", observed_evidence)
        self.assertIn("exact-ranking", observed_evidence)
        self.assertIn("byte-vector-subset", observed_evidence)
        self.assertIn("binary-vector-subset", observed_evidence)
        self.assertIn("nested-filtered-knn", observed_evidence)
        self.assertIn("hybrid-score-merge", observed_evidence)

    def test_vector_promotion_gate_requires_case_extracts_for_every_semantic_case(self):
        fixture_path = (
            Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "vector-promotion-gate.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        semantic = fixture["unified_report_sections"]["semantic_parity"]

        self.assertEqual(
            set(semantic["required_case_extracts"]),
            set(semantic["required_cases"]),
        )

    def test_search_fixture_carries_knn_plugin_report_bound_evidence(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "search-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        expected = {
            "knn_settings_readback": {"method-boundary"},
            "knn_warmup_basic_shape": {"warmup-cache"},
            "knn_clear_cache_basic_shape": {"clear-cache"},
            "knn_model_lifecycle_shape": {"model-lifecycle"},
            "knn_warmup_post_method_not_allowed": {"method-boundary"},
            "knn_warmup_clear_cache_telemetry_shape": {"warmup-cache", "clear-cache"},
        }
        for case_name, evidence_classes in expected.items():
            self.assertIn(case_name, cases)
            metadata = cases[case_name].get("metadata") or {}
            self.assertEqual(set(metadata.get("evidence_classes") or []), evidence_classes)

    def test_knn_plugin_promotion_gate_requires_case_extracts_for_every_semantic_case(self):
        fixture_path = (
            Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "knn-plugin-promotion-gate.json"
        )
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        semantic = fixture["unified_report_sections"]["semantic_parity"]

        self.assertEqual(
            set(semantic["required_case_extracts"]),
            set(semantic["required_cases"]),
        )

    def test_ml_fixture_carries_lifecycle_aggregate_evidence(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "ml-model-surface-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        aggregate = fixture.get("aggregate_case") or {}

        self.assertEqual(aggregate.get("name"), "ml_model_lifecycle_shape")
        self.assertEqual(
            set(aggregate.get("metadata", {}).get("evidence_classes") or []),
            {
                "model-group-lifecycle",
                "task-lifecycle",
                "connector-lifecycle",
                "deploy-persistence",
                "neural-query-rewrite",
                "rerank-pipeline",
                "neural-sparse-raw",
            },
        )
        self.assertEqual(
            set(aggregate.get("required_cases") or []),
            {
                "register_model_group",
                "get_model_group",
                "register_model",
                "get_register_task",
                "create_connector",
                "get_connector",
                "get_model",
                "deploy_model",
                "get_deploy_task",
                "predict_model",
                "search_model",
                "neural_query_search",
                "put_rerank_pipeline",
                "rerank_pipeline_search",
                "neural_sparse_raw_search",
                "undeploy_model",
            },
        )

    def test_security_fixture_carries_ml_authz_evidence(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "security-authz-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        expected = {
            "security_bad_password_ml_register_401": {"runtime-isolation"},
            "security_writer_ml_connector_create_403": {"connector-authz"},
            "security_admin_ml_connector_create_success": {"connector-authz"},
            "security_writer_ml_predict_403": {"deployment-isolation"},
        }
        for case_name, evidence_classes in expected.items():
            self.assertIn(case_name, cases)
            metadata = cases[case_name].get("metadata") or {}
            self.assertEqual(set(metadata.get("evidence_classes") or []), evidence_classes)

    def test_security_fixture_covers_restricted_system_prefixes_and_wildcard(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "security-authz-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        required = {
            "security_admin_restricted_tasks_search_allowed",
            "security_reader_restricted_tasks_search_403",
            "security_admin_restricted_security_settings_allowed",
            "security_reader_restricted_security_settings_403",
            "security_admin_wildcard_restricted_search_allowed",
            "security_reader_wildcard_restricted_search_403",
        }

        self.assertTrue(required <= set(cases), sorted(required - set(cases)))
        self.assertEqual(
            cases["security_reader_restricted_tasks_search_403"]["path"],
            "/.tasks-restricted-authz*/_search",
        )
        self.assertEqual(
            cases["security_reader_restricted_security_settings_403"]["path"],
            "/.security-restricted-authz*/_settings",
        )
        self.assertEqual(cases["security_reader_wildcard_restricted_search_403"]["path"], "/*/_search")

    def test_alias_fixture_carries_global_and_collection_route_variants(self):
        fixture_path = Path(__file__).resolve().parents[1] / "tools" / "fixtures" / "alias-read-compat.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        cases = {case["name"]: case for case in fixture["cases"]}

        expected_routes = {
            "head_global_alias_named_route": ("HEAD", "/_alias/logs-compat-write"),
            "put_global_alias_named_route_with_index_body": ("PUT", "/_alias/logs-compat-global"),
            "post_global_aliases_named_route_with_index_body": (
                "POST",
                "/_aliases/metrics-compat-global",
            ),
            "put_index_alias_collection_route_with_alias_body": (
                "PUT",
                "/logs-compat-alias-000001/_alias",
            ),
            "get_alias_global_collection_readback": ("GET", "/_alias"),
        }
        for case_name, (method, path) in expected_routes.items():
            self.assertIn(case_name, cases)
            self.assertEqual(cases[case_name]["method"], method)
            self.assertEqual(cases[case_name]["path"], path)


if __name__ == "__main__":
    unittest.main()
