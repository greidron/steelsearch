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


if __name__ == "__main__":
    unittest.main()
