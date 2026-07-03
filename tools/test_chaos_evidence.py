import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHAOS_PATH = ROOT / "tools" / "generate-chaos-evidence.py"


def load_chaos_module():
    module_name = "generate_chaos_evidence"
    spec = importlib.util.spec_from_file_location(module_name, CHAOS_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ChaosEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.chaos = load_chaos_module()

    def test_validate_source_report_accepts_required_checks(self):
        report = {
            "summary": {"passed": True},
            "checks": {
                "failure_topology_probe_passed": True,
                "failure_ledger_passed": True,
                "pit_restart_lifecycle_passed": True,
                "pit_transport_restart_lifecycle_passed": True,
                "pit_multi_daemon_lifecycle_passed": True,
            },
            "reports": {"failure_topology_probe_report": "probe.json"},
            "executed_tests": [
                "daemon_point_in_time_contexts_do_not_survive_restart",
                "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                "multi_daemon_get_all_pits_fans_out_to_seed_peers",
            ],
        }

        self.assertEqual(self.chaos.validate_source_report(report), [])

    def test_validate_source_report_rejects_failed_child_check(self):
        report = {
            "summary": {"passed": True},
            "checks": {
                "failure_topology_probe_passed": True,
                "failure_ledger_passed": False,
                "pit_restart_lifecycle_passed": True,
                "pit_transport_restart_lifecycle_passed": True,
                "pit_multi_daemon_lifecycle_passed": True,
            },
            "reports": {"failure_topology_probe_report": "probe.json"},
            "executed_tests": [
                "daemon_point_in_time_contexts_do_not_survive_restart",
                "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                "multi_daemon_get_all_pits_fans_out_to_seed_peers",
            ],
        }

        errors = self.chaos.validate_source_report(report)

        self.assertIn(
            "mixed-cluster failure check is not true: failure_ledger_passed",
            errors,
        )

    def test_validate_source_report_rejects_missing_pit_lifecycle_checks(self):
        report = {
            "summary": {"passed": True},
            "checks": {
                "failure_topology_probe_passed": True,
                "failure_ledger_passed": True,
            },
            "reports": {"failure_topology_probe_report": "probe.json"},
            "executed_tests": [
                "daemon_point_in_time_contexts_do_not_survive_restart",
                "daemon_transport_point_in_time_contexts_do_not_survive_restart",
                "multi_daemon_get_all_pits_fans_out_to_seed_peers",
            ],
        }

        errors = self.chaos.validate_source_report(report)

        self.assertIn(
            "mixed-cluster failure checks are missing: pit_multi_daemon_lifecycle_passed, pit_restart_lifecycle_passed, pit_transport_restart_lifecycle_passed",
            errors,
        )

    def test_validate_source_report_rejects_missing_executed_pit_fanout_test(self):
        report = {
            "summary": {"passed": True},
            "checks": {
                "failure_topology_probe_passed": True,
                "failure_ledger_passed": True,
                "pit_restart_lifecycle_passed": True,
                "pit_transport_restart_lifecycle_passed": True,
                "pit_multi_daemon_lifecycle_passed": True,
            },
            "reports": {"failure_topology_probe_report": "probe.json"},
            "executed_tests": [],
        }

        errors = self.chaos.validate_source_report(report)

        self.assertIn(
            "mixed-cluster failure executed_tests are missing: daemon_point_in_time_contexts_do_not_survive_restart, daemon_transport_point_in_time_contexts_do_not_survive_restart, multi_daemon_get_all_pits_fans_out_to_seed_peers",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
