import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/source-compatibility.yml"


class SourceCompatibilityWorkflowTests(unittest.TestCase):
    def test_source_compatibility_workflow_triggers_on_gate_tools(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        required_paths = [
            "tools/check-source-compatibility-drift.sh",
            "tools/check-search-extension-point-contracts.py",
            "tools/check-node-runtime-boundary-contracts.py",
            "tools/check-source-partial-promotion-readiness.py",
            "tools/report-rest-api-coverage.py",
            "tools/report-transport-action-coverage.py",
            "tools/fixtures/**",
        ]
        for path in required_paths:
            self.assertGreaterEqual(
                workflow.count(f'"{path}"'),
                2,
                f"{path} should trigger both pull_request and push workflow runs",
            )

    def test_generated_drift_job_runs_single_source_compatibility_gate(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("Check generated source compatibility TSVs", workflow)
        self.assertIn("tools/check-source-compatibility-drift.sh", workflow)


if __name__ == "__main__":
    unittest.main()
