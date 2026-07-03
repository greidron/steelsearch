import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-source-compatibility-gaps.py"
CURRENT_MATRIX = ROOT / "docs" / "rust-port" / "generated" / "source-compatibility-matrix.tsv"


def load_report_module():
    module_name = "report_source_compatibility_gaps"
    spec = importlib.util.spec_from_file_location(module_name, REPORT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceCompatibilityGapReportTests(unittest.TestCase):
    def setUp(self):
        self.reporter = load_report_module()

    def test_current_matrix_has_all_open_gaps_mapped_to_owner_docs(self):
        report = self.reporter.report_gaps(CURRENT_MATRIX)

        self.assertEqual(report["status"], "ok")
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["summary"]["open_gap_row_count"], 85)
        self.assertEqual(
            report["summary"]["open_gap_counts"],
            {
                "node_runtime": {"partial": 72, "planned": 6},
                "search_registration": {"partial": 7},
            },
        )

    def test_unmapped_open_gap_fails_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            matrix = Path(temp_dir_value) / "source-compatibility-matrix.tsv"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "transport_action\tpartial\taction\tSearchAction.INSTANCE\tTransportSearchAction.class\tActionModule.java\t10\n",
                encoding="utf-8",
            )

            report = self.reporter.report_gaps(matrix)

            self.assertEqual(report["status"], "failed")
            self.assertEqual(report["summary"]["unmapped_gap_count"], 1)
            self.assertIn("transport_action/partial", report["errors"][0])

    def test_closed_rows_do_not_require_gap_owner(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            matrix = Path(temp_dir_value) / "source-compatibility-matrix.tsv"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "rest_route\timplemented\tGET\t/_search\t\tRestSearchAction.java\t10\n"
                "rest_route\tout-of-scope\tGET\t/_dashboards\t\tDashboards.java\t20\n",
                encoding="utf-8",
            )

            report = self.reporter.report_gaps(matrix)

            self.assertEqual(report["status"], "ok")
            self.assertEqual(report["summary"]["open_gap_row_count"], 0)


if __name__ == "__main__":
    unittest.main()
