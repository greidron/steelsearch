import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = ROOT / "tools" / "report-source-compatibility-gaps.py"
CURRENT_MATRIX = ROOT / "docs" / "rust-port" / "generated" / "source-compatibility-matrix.tsv"
SOURCE_COMPATIBILITY_DOC = ROOT / "docs" / "rust-port" / "source-compatibility-matrix.md"
REPLACEMENT_EXIT_CRITERIA_DOC = (
    ROOT / "docs" / "rust-port" / "replacement-claim-exit-criteria.md"
)


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
        self.assertEqual(report["summary"]["open_gap_row_count"], 0)
        self.assertEqual(
            report["summary"]["open_gap_counts"],
            {},
        )

    def test_replacement_readiness_summary_matches_current_native_closure_gate(self):
        source_matrix = SOURCE_COMPATIBILITY_DOC.read_text(encoding="utf-8")
        exit_criteria = REPLACEMENT_EXIT_CRITERIA_DOC.read_text(encoding="utf-8")

        self.assertNotIn(
            "| Production OpenSearch cluster replacement | Not ready. |",
            source_matrix,
        )
        self.assertNotIn(
            "| Production OpenSearch API parity | Not ready. |",
            source_matrix,
        )
        self.assertIn(
            "| Production OpenSearch cluster replacement | Ready for the supported",
            source_matrix,
        )
        self.assertIn(
            "| Production OpenSearch API parity | Ready for the supported",
            source_matrix,
        )
        self.assertIn("native-closure-status-current", exit_criteria)
        self.assertIn("current_evidence_ready=true", exit_criteria)
        self.assertIn("final_cutover_ready=true", exit_criteria)

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
