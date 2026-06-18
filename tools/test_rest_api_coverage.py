import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-rest-api-coverage.py"


def load_report_module():
    module_name = "report_rest_api_coverage"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class RestApiCoverageTests(unittest.TestCase):
    def setUp(self):
        self.report = load_report_module()

    def test_template_source_route_matches_concrete_fixture_path(self):
        source = [
            {
                "status": "implemented",
                "method": "POST",
                "path": "/{index}/_search",
                "source": "ActionModule.java",
                "line": "1",
            },
            {
                "status": "planned",
                "method": "GET",
                "path": "/_cat/shards",
                "source": "ActionModule.java",
                "line": "2",
            },
        ]
        observed = [
            {
                "method": "POST",
                "path": "/logs-000001/_search?size=1",
                "fixture": "fixture.json",
            }
        ]

        coverage = self.report.coverage_for_routes(source, observed)

        self.assertEqual(len(coverage["matched_source_route_keys"]), 1)
        self.assertEqual(
            coverage["uncovered_in_scope_source_routes"],
            [source[1]],
        )

    def test_live_required_fixture_paths_only_uses_ok_required_suites(self):
        report = {
            "suite_results": [
                {
                    "name": "search",
                    "required": True,
                    "status": "ok",
                    "fixture_path": "/tmp/search.json",
                },
                {
                    "name": "optional",
                    "required": False,
                    "status": "ok",
                    "fixture_path": "/tmp/optional.json",
                },
                {
                    "name": "missing",
                    "required": True,
                    "status": "missing",
                    "fixture_path": "/tmp/missing.json",
                },
            ]
        }

        self.assertEqual(
            self.report.live_required_fixture_paths(report),
            [Path("/tmp/search.json")],
        )

    def test_cli_writes_coverage_summary(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source.tsv"
            fixtures = temp_dir / "fixtures"
            fixtures.mkdir()
            output = temp_dir / "coverage.json"
            source.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                "implemented\tPOST\t/{index}/_search\tActionModule.java\t1\n"
                "planned\tGET\t/_cat/shards\tActionModule.java\t2\n",
                encoding="utf-8",
            )
            fixture = fixtures / "search.json"
            fixture.write_text(
                json.dumps(
                    {
                        "cases": [
                            {
                                "name": "search",
                                "method": "POST",
                                "path": "/logs-000001/_search",
                            }
                        ]
                    }
                )
                + "\n",
                encoding="utf-8",
            )

            result = self.run_cli(
                "--source",
                str(source),
                "--fixtures-dir",
                str(fixtures),
                "--output",
                str(output),
            )

            self.assertEqual(result, 0)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["fixture_matched_source_route_count"], 1)
            self.assertEqual(payload["summary"]["fixture_uncovered_in_scope_route_count"], 1)

    def run_cli(self, *args: str) -> int:
        old_argv = sys.argv
        try:
            sys.argv = [str(REPORT_PATH), *args]
            return self.report.main()
        finally:
            sys.argv = old_argv


if __name__ == "__main__":
    unittest.main()
