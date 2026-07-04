import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-compatibility-matrix-coverage.py"


def load_checker_module():
    module_name = "check_source_compatibility_matrix_coverage"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceCompatibilityMatrixCoverageTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_matrix_covering_all_source_inventory_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            write_inventory_set(temp_dir)
            matrix = temp_dir / "source-compatibility-matrix.tsv"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "rest_route\timplemented\tGET\t/_search\t\tRestSearchAction.java\t10\n"
                "transport_action\timplemented\taction\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t20\n"
                "search_registration\timplemented\tquery\tnew QuerySpec<>(MatchQueryBuilder.NAME)\t\tSearchModule.java\t30\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t40\n",
                encoding="utf-8",
            )

            result = self.checker.validate_matrix(matrix, temp_dir)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["summary"]["matrix_row_count"], 4)
            self.assertEqual(result["summary"]["expected_row_count"], 4)
            self.assertEqual(result["summary"]["status_counts"], {"implemented": 3, "partial": 1})
            self.assertEqual(result["summary"]["missing_transport_anchor_surface_count"], 0)
            self.assertEqual(result["summary"]["missing_rest_anchor_surface_count"], 0)

    def test_rejects_matrix_missing_source_inventory_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            write_inventory_set(temp_dir)
            matrix = temp_dir / "source-compatibility-matrix.tsv"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "rest_route\timplemented\tGET\t/_search\t\tRestSearchAction.java\t10\n",
                encoding="utf-8",
            )

            result = self.checker.validate_matrix(matrix, temp_dir)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["missing_row_count"], 3)
            self.assertIn("transport_action", json.dumps(result["errors"]))

    def test_rejects_unknown_surface_status_and_category(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            write_inventory_set(temp_dir)
            matrix = temp_dir / "source-compatibility-matrix.tsv"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "rest_route\texperimental\tPATCH\t/_search\t\tRestSearchAction.java\t10\n"
                "unknown_surface\timplemented\tunknown_category\tThing\t\tThing.java\t50\n",
                encoding="utf-8",
            )

            result = self.checker.validate_matrix(matrix, temp_dir)

            self.assertEqual(result["status"], "failed")
            errors = "\n".join(result["errors"])
            self.assertIn("invalid status: 'experimental'", errors)
            self.assertIn("invalid category for 'rest_route': 'PATCH'", errors)
            self.assertIn("invalid surface: 'unknown_surface'", errors)
            self.assertIn("invalid category for 'unknown_surface': 'unknown_category'", errors)

    def test_transport_action_source_anchor_surface_missing_tokens_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            runtime = Path(temp_dir_value) / "standalone_runtime.rs"
            runtime.write_text("", encoding="utf-8")

            missing = self.checker.transport_action_source_anchor_surface_missing(runtime)

            self.assertEqual(
                missing,
                [
                    "generated TSV include",
                    "source anchor struct",
                    "source anchor status field",
                    "source anchor action field",
                    "source anchor transport handler field",
                    "source anchor source field",
                    "source anchor line field",
                    "source anchor function",
                    "dev endpoint key",
                ],
            )

    def test_rest_route_source_anchor_surface_missing_tokens_are_reported(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            runtime = Path(temp_dir_value) / "standalone_runtime.rs"
            runtime.write_text("", encoding="utf-8")

            missing = self.checker.rest_route_source_anchor_surface_missing(runtime)

            self.assertEqual(
                missing,
                [
                    "generated TSV include",
                    "source anchor struct",
                    "source anchor status field",
                    "source anchor method field",
                    "source anchor path field",
                    "source anchor source field",
                    "source anchor line field",
                    "source anchor function",
                    "dev endpoint key",
                ],
            )


def write_inventory_set(temp_dir: Path) -> None:
    (temp_dir / "source-rest-routes.tsv").write_text(
        "status\tmethod\tpath_or_expression\tsource\tline\n"
        "implemented\tGET\t/_search\tRestSearchAction.java\t10\n",
        encoding="utf-8",
    )
    (temp_dir / "source-transport-actions.tsv").write_text(
        "status\taction\ttransport_handler\tsource\tline\n"
        "implemented\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t20\n",
        encoding="utf-8",
    )
    (temp_dir / "source-search-registrations.tsv").write_text(
        "status\tcategory\texpression\tsource\tline\n"
        "implemented\tquery\tnew QuerySpec<>(MatchQueryBuilder.NAME)\tSearchModule.java\t30\n",
        encoding="utf-8",
    )
    (temp_dir / "source-node-runtime-components.tsv").write_text(
        "status\tkind\tcomponent\tsource\tline\n"
        "partial\tservice\tSearchService\tNode.java\t40\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
