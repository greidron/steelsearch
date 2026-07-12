import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-external-interop-promotion-gate.py"
FIXTURE_PATH = ROOT / "tools" / "fixtures" / "external-interop-promotion-gate.json"


def load_checker_module():
    module_name = "check_external_interop_promotion_gate"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class ExternalInteropPromotionGateTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_current_external_interop_promotion_gate_passes(self):
        original_argv = sys.argv
        try:
            sys.argv = [str(CHECKER_PATH), str(FIXTURE_PATH)]
            self.checker.main()
        finally:
            sys.argv = original_argv

    def test_rejects_missing_handshake_reject_route_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
            fixture["unified_report_sections"]["route_parity"]["required_reports"] = [
                "phase-b-gap/<profile>/report.json"
            ]
            path = temp_dir / "external-interop-promotion-gate.json"
            path.write_text(json.dumps(fixture), encoding="utf-8")

            original_argv = sys.argv
            try:
                sys.argv = [str(CHECKER_PATH), str(path)]
                with self.assertRaisesRegex(SystemExit, "route reports mismatch"):
                    self.checker.main()
            finally:
                sys.argv = original_argv

    def test_rejects_handshake_reject_fixture_class_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            reject_fixture = temp_dir / "interop-handshake-reject-cases.json"
            reject_fixture.write_text(
                json.dumps(
                    {
                        "name": "interop-handshake-reject-cases",
                        "cases": [
                            {
                                "name": "bad_tcp_handshake_frame",
                                "class": "bad-handshake",
                                "expected_decision": "reject",
                                "expected_markers": ["handshake decode failed"],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            original_fixture_path = self.checker.fixture_path
            try:
                self.checker.fixture_path = lambda name: reject_fixture
                with self.assertRaisesRegex(SystemExit, "handshake reject cases mismatch"):
                    self.checker.validate_handshake_reject_cases(
                        "interop-handshake-reject-cases.json"
                    )
            finally:
                self.checker.fixture_path = original_fixture_path


if __name__ == "__main__":
    unittest.main()
