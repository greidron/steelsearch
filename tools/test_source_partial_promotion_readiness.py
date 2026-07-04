import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-partial-promotion-readiness.py"
CURRENT_MATRIX = ROOT / "docs/rust-port/generated/source-compatibility-matrix.tsv"
CURRENT_LEDGER = ROOT / "tools/fixtures/source-partial-promotion-readiness.json"


def load_checker_module():
    module_name = "check_source_partial_promotion_readiness"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourcePartialPromotionReadinessTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_current_partial_groups_have_readiness_entries(self):
        result = self.checker.check_readiness(CURRENT_MATRIX, CURRENT_LEDGER)

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["summary"]["matrix_partial_group_count"], 10)
        self.assertEqual(result["summary"]["ledger_entry_count"], 10)
        self.assertEqual(result["summary"]["matrix_partial_row_count"], 85)
        self.assertEqual(result["summary"]["ledger_expected_row_count"], 85)
        self.assertEqual(result["summary"]["missing_group_count"], 0)
        self.assertEqual(result["summary"]["extra_group_count"], 0)
        self.assertEqual(result["summary"]["duplicate_group_count"], 0)
        self.assertEqual(
            result["summary"]["bucket_counts"],
            {"promotion-blocked": 6, "promotion-ready": 4},
        )
        self.assertEqual(
            result["summary"]["current_evidence_class_counts"],
            {
                "boundary mapping": 10,
                "durability parity": 1,
                "route parity": 3,
                "semantic parity": 8,
            },
        )
        self.assertEqual(
            result["summary"]["missing_required_class_counts"],
            {
                "distributed parity": 4,
                "durability parity": 2,
                "semantic parity": 2,
            },
        )
        self.assertGreaterEqual(result["summary"]["evidence_artifact_count"], 30)

    def test_missing_or_wrong_count_entry_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            matrix = temp_dir / "matrix.tsv"
            ledger = temp_dir / "ledger.json"
            (temp_dir / "gate.py").write_text("# gate\n", encoding="utf-8")
            (temp_dir / "evidence.json").write_text("{}\n", encoding="utf-8")
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t1\n"
                "search_registration\tpartial\tquery\tQuerySpec<?> spec\t\tSearchModule.java\t2\n",
                encoding="utf-8",
            )
            ledger.write_text(
                """
{
  "entries": [
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "service",
      "expected_count": 2,
      "promotion_bucket": "promotion-blocked",
      "current_contract_gate": "gate.py",
      "current_evidence_artifacts": ["evidence.json"],
      "current_evidence_classes": ["boundary mapping"],
      "missing_required_classes": ["semantic parity"],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
  ]
}
""",
                encoding="utf-8",
            )

            result = self.checker.check_readiness(matrix, ledger)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["missing_group_count"], 1)
            self.assertTrue(any("expected_count" in error for error in result["errors"]))
            self.assertTrue(any("missing readiness entries" in error for error in result["errors"]))

    def test_duplicate_and_extra_entries_fail(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            matrix = temp_dir / "matrix.tsv"
            ledger = temp_dir / "ledger.json"
            (temp_dir / "gate.py").write_text("# gate\n", encoding="utf-8")
            (temp_dir / "evidence.json").write_text("{}\n", encoding="utf-8")
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t1\n",
                encoding="utf-8",
            )
            entry = """
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "service",
      "expected_count": 1,
      "promotion_bucket": "promotion-blocked",
      "current_contract_gate": "gate.py",
      "current_evidence_artifacts": ["evidence.json"],
      "current_evidence_classes": ["boundary mapping"],
      "missing_required_classes": ["semantic parity"],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
"""
            extra = """
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "module",
      "expected_count": 1,
      "promotion_bucket": "promotion-ready",
      "current_contract_gate": "gate.py",
      "current_evidence_artifacts": ["evidence.json"],
      "current_evidence_classes": ["boundary mapping"],
      "missing_required_classes": ["semantic parity"],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
"""
            ledger.write_text(
                '{"entries": [' + entry + "," + entry + "," + extra + "]}",
                encoding="utf-8",
            )

            result = self.checker.check_readiness(matrix, ledger)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["duplicate_group_count"], 1)
            self.assertEqual(result["summary"]["extra_group_count"], 1)

    def test_missing_gate_or_evidence_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            matrix = temp_dir / "matrix.tsv"
            ledger = temp_dir / "ledger.json"
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t1\n",
                encoding="utf-8",
            )
            ledger.write_text(
                """
{
  "entries": [
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "service",
      "expected_count": 1,
      "promotion_bucket": "promotion-blocked",
      "current_contract_gate": "missing-gate.py",
      "current_evidence_artifacts": ["missing-evidence.json"],
      "current_evidence_classes": ["boundary mapping"],
      "missing_required_classes": ["semantic parity"],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
  ]
}
""",
                encoding="utf-8",
            )

            result = self.checker.check_readiness(matrix, ledger)

            self.assertEqual(result["status"], "failed")
            self.assertTrue(any("current_contract_gate does not exist" in error for error in result["errors"]))
            self.assertTrue(any("evidence artifact does not exist" in error for error in result["errors"]))

    def test_unsupported_evidence_class_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            matrix = temp_dir / "matrix.tsv"
            ledger = temp_dir / "ledger.json"
            (temp_dir / "gate.py").write_text("# gate\n", encoding="utf-8")
            (temp_dir / "evidence.json").write_text("{}\n", encoding="utf-8")
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t1\n",
                encoding="utf-8",
            )
            ledger.write_text(
                """
{
  "entries": [
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "service",
      "expected_count": 1,
      "promotion_bucket": "promotion-blocked",
      "current_contract_gate": "gate.py",
      "current_evidence_artifacts": ["evidence.json"],
      "current_evidence_classes": ["imaginary parity"],
      "missing_required_classes": ["semantic parity"],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
  ]
}
""",
                encoding="utf-8",
            )

            result = self.checker.check_readiness(matrix, ledger)

            self.assertEqual(result["status"], "failed")
            self.assertTrue(
                any("unsupported current_evidence_classes" in error for error in result["errors"])
            )

    def test_declared_missing_required_classes_must_match_computed_gap(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            matrix = temp_dir / "matrix.tsv"
            ledger = temp_dir / "ledger.json"
            (temp_dir / "gate.py").write_text("# gate\n", encoding="utf-8")
            (temp_dir / "evidence.json").write_text("{}\n", encoding="utf-8")
            matrix.write_text(
                "surface\tstatus\tcategory\tidentifier\tdetail\tsource\tline\n"
                "node_runtime\tpartial\tservice\tSearchService\t\tNode.java\t1\n",
                encoding="utf-8",
            )
            ledger.write_text(
                """
{
  "entries": [
    {
      "surface": "node_runtime",
      "status": "partial",
      "category": "service",
      "expected_count": 1,
      "promotion_bucket": "promotion-blocked",
      "current_contract_gate": "gate.py",
      "current_evidence_artifacts": ["evidence.json"],
      "current_evidence_classes": ["boundary mapping"],
      "missing_required_classes": [],
      "required_for_implemented": ["semantic parity"],
      "blocker": "blocked"
    }
  ]
}
""",
                encoding="utf-8",
            )

            result = self.checker.check_readiness(matrix, ledger)

            self.assertEqual(result["status"], "failed")
            self.assertTrue(
                any("missing_required_classes" in error for error in result["errors"])
            )
            self.assertTrue(
                any("promotion-blocked entries must declare" in error for error in result["errors"])
            )


if __name__ == "__main__":
    unittest.main()
