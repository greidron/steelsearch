import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DRIFT_SCRIPT = ROOT / "tools" / "check-source-compatibility-drift.sh"


class SourceCompatibilityDriftScriptTests(unittest.TestCase):
    def test_drift_script_runs_all_generated_tsv_diffs(self):
        script = DRIFT_SCRIPT.read_text(encoding="utf-8")

        for tsv_name in (
            "source-rest-routes.tsv",
            "source-transport-actions.tsv",
            "source-search-registrations.tsv",
            "source-node-runtime-components.tsv",
            "source-compatibility-matrix.tsv",
        ):
            self.assertIn(f'docs/rust-port/generated/{tsv_name}', script)
            self.assertIn(f'${{TMP_DIR}}/{tsv_name}', script)

    def test_drift_script_runs_all_source_line_and_matrix_checkers(self):
        script = DRIFT_SCRIPT.read_text(encoding="utf-8")

        required_checkers = [
            "check-source-rest-route-lines.py",
            "check-source-transport-action-lines.py",
            "check-source-search-registration-lines.py",
            "check-search-extension-point-contracts.py",
            "check-source-node-runtime-lines.py",
            "check-node-runtime-boundary-contracts.py",
            "check-source-compatibility-matrix-coverage.py",
        ]
        for checker in required_checkers:
            self.assertIn(f"tools/{checker}", script)

        positions = [script.index(checker) for checker in required_checkers]
        self.assertEqual(positions, sorted(positions))

    def test_drift_script_regenerates_before_comparing(self):
        script = DRIFT_SCRIPT.read_text(encoding="utf-8")

        self.assertIn('OUT_DIR="${TMP_DIR}" "${ROOT}/tools/source-compatibility-matrix.sh"', script)
        self.assertLess(
            script.index("source-compatibility-matrix.sh"),
            script.index("diff -u"),
        )


if __name__ == "__main__":
    unittest.main()
