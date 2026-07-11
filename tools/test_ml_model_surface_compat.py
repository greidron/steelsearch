import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "tools" / "ml_model_surface_compat.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ml_model_surface_compat_test", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules["ml_model_surface_compat_test"] = module
    spec.loader.exec_module(module)
    return module


class MlModelSurfaceCompatTests(unittest.TestCase):
    def test_steelsearch_only_fixture_still_reports_passed_cases(self):
        ml = load_module()
        fixture = {
            "name": "ml-model-surface-compat",
            "cases": [
                {
                    "name": "register_model",
                    "method": "POST",
                    "path": "/_plugins/_ml/models/_register",
                    "expected_status": 200,
                    "compare_paths": ["model_id"],
                    "expected_paths": {"model_id": "model-1"},
                    "metadata": {"evidence_class": "model-group-lifecycle"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "fixture.json"
            report_path = Path(tmp) / "report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            original_argv = sys.argv
            original_request = ml.request_json
            try:
                sys.argv = [
                    "ml",
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--fixture",
                    str(fixture_path),
                    "--output",
                    str(report_path),
                ]
                ml.request_json = lambda *_args, **_kwargs: {
                    "status": 200,
                    "body": {"model_id": "model-1"},
                    "body_text": '{"model_id":"model-1"}',
                }
                self.assertEqual(ml.main(), 0)
            finally:
                sys.argv = original_argv
                ml.request_json = original_request

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["summary"], {"failed": 0, "passed": 1, "skipped": 0})
        self.assertEqual(report["targets"], {"steelsearch": "http://steelsearch"})
        self.assertEqual(report["cases"][0]["status"], "passed")

    def test_missing_opensearch_ml_plugin_marks_comparison_as_degraded_skip(self):
        ml = load_module()
        fixture = {
            "name": "ml-model-surface-compat",
            "cases": [
                {
                    "name": "register_model",
                    "method": "POST",
                    "path": "/_plugins/_ml/models/_register",
                    "expected_status": 200,
                    "compare_paths": ["model_id"],
                    "expected_paths": {"model_id": "model-1"},
                    "metadata": {"evidence_class": "model-group-lifecycle"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "fixture.json"
            report_path = Path(tmp) / "report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            original_argv = sys.argv
            original_request = ml.request_json

            def fake_request(base_url, _method, path, _body, _timeout):
                if base_url == "http://opensearch" and path.startswith("/_plugins/_ml/"):
                    return {
                        "status": 400,
                        "body": {
                            "error": {
                                "reason": (
                                    "no handler found for uri "
                                    "[/_plugins/_ml/models/_register] and method [POST]"
                                )
                            }
                        },
                        "body_text": "",
                    }
                return {
                    "status": 200,
                    "body": {"model_id": "model-1"},
                    "body_text": '{"model_id":"model-1"}',
                }

            try:
                sys.argv = [
                    "ml",
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--opensearch-url",
                    "http://opensearch",
                    "--fixture",
                    str(fixture_path),
                    "--output",
                    str(report_path),
                ]
                ml.request_json = fake_request
                self.assertEqual(ml.main(), 0)
            finally:
                sys.argv = original_argv
                ml.request_json = original_request

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["summary"], {"failed": 0, "passed": 0, "skipped": 1})
        self.assertEqual(report["targets"]["opensearch"], "http://opensearch")
        self.assertEqual(report["cases"][0]["status"], "skipped")
        self.assertIn("ML Commons plugin surface", report["cases"][0]["skipped_reason"])

    def test_opensearch_case_mismatch_preserves_steelsearch_only_pass(self):
        ml = load_module()
        fixture = {
            "name": "ml-model-surface-compat",
            "cases": [
                {
                    "name": "register_model",
                    "method": "POST",
                    "path": "/_plugins/_ml/models/_register",
                    "expected_status": 200,
                    "compare_paths": ["model_id"],
                    "expected_paths": {"model_id": "model-1"},
                    "metadata": {"evidence_class": "model-group-lifecycle"},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "fixture.json"
            report_path = Path(tmp) / "report.json"
            fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
            original_argv = sys.argv
            original_request = ml.request_json

            def fake_request(base_url, _method, _path, _body, _timeout):
                if base_url == "http://opensearch":
                    return {"status": 400, "body": {"error": {"reason": "unsupported fixture shape"}}, "body_text": ""}
                return {"status": 200, "body": {"model_id": "model-1"}, "body_text": '{"model_id":"model-1"}'}

            try:
                sys.argv = [
                    "ml",
                    "--steelsearch-url",
                    "http://steelsearch",
                    "--opensearch-url",
                    "http://opensearch",
                    "--fixture",
                    str(fixture_path),
                    "--output",
                    str(report_path),
                ]
                ml.request_json = fake_request
                self.assertEqual(ml.main(), 0)
            finally:
                sys.argv = original_argv
                ml.request_json = original_request

            report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["summary"], {"failed": 0, "passed": 1, "skipped": 0})
        self.assertEqual(report["cases"][0]["status"], "passed")
        self.assertEqual(report["cases"][0]["mode"], "steelsearch-only")
        self.assertIn("opensearch_unmatched", report["cases"][0])
        self.assertNotIn("opensearch", report["cases"][0])
        self.assertEqual(report["cases"][0]["metadata"]["evidence_class"], "model-group-lifecycle")

    def test_undeploy_stats_derived_comparison_ignores_dynamic_node_id(self):
        ml = load_module()
        case = {
            "name": "undeploy_model",
            "expected_status": 200,
            "compare_paths": ["_derived.undeploy_model_state"],
            "expected_paths": {
                "_derived.undeploy_model_state": {
                    "model_id": "${register_model.model_id}",
                    "state": "UNDEPLOYED",
                }
            },
        }
        results = {"register_model": {"body": {"model_id": "model-123"}}}
        response = {
            "status": 200,
            "body": {
                "node-A": {
                    "stats": {
                        "model-123": "UNDEPLOYED",
                    }
                }
            },
        }

        summary, errors = ml.summarize_case_response(case, response, results)

        self.assertEqual(summary["_derived.undeploy_model_state"], "UNDEPLOYED")
        self.assertEqual(errors, [])


if __name__ == "__main__":
    unittest.main()
