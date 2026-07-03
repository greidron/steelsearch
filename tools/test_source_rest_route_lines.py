import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-rest-route-lines.py"


def load_checker_module():
    module_name = "check_source_rest_route_lines"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceRestRouteLinesTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_quoted_java_route_expression(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "RestRankEvalAction.java"
            source.write_text(
                'new Route(GET, "/" + ENDPOINT),\n'
                'new Route(POST, "/{index}/" + ENDPOINT),\n',
                encoding="utf-8",
            )
            tsv = temp_dir / "source-rest-routes.tsv"
            tsv.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                f"implemented\tGET\t/ + ENDPOINT\t{source}\t1\n"
                f"implemented\tPOST\t/{{index}}/ + ENDPOINT\t{source}\t2\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["summary"]["checked_rows"], 2)

    def test_rejects_row_whose_method_or_path_is_not_in_source_window(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "RestSearchAction.java"
            source.write_text('new Route(GET, "/_search"),\n', encoding="utf-8")
            tsv = temp_dir / "source-rest-routes.tsv"
            tsv.write_text(
                "status\tmethod\tpath_or_expression\tsource\tline\n"
                f"implemented\tPOST\t/_missing\t{source}\t1\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "failed")
            self.assertIn("POST", json.dumps(result["errors"]))
            self.assertIn("/_missing", json.dumps(result["errors"]))


if __name__ == "__main__":
    unittest.main()
