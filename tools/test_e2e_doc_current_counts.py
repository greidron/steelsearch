import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-e2e-doc-current-counts.py"
spec = importlib.util.spec_from_file_location("check_e2e_doc_current_counts", CHECKER_PATH)
checker = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(checker)


def broad_report():
    return {
        "status": "ok",
        "suite_results": [
            {"name": "search-compat", "summary": {"passed": 10, "failed": 0, "skipped": 2}},
            {"name": "search-strict", "summary": {"passed": 8, "failed": 0, "skipped": 1}},
            {"name": "search-semantic", "summary": {"passed": 3, "failed": 0, "skipped": 0}},
        ],
        "coverage_summary": {
            "effective_case_classification": {
                "canonical_equal": 11,
                "strict_equal": 7,
                "semantic_equal": 3,
                "steelsearch_only": 0,
                "known_gap_or_skipped": 0,
                "failed": 0,
                "missing": 0,
            },
            "case_gap_resolution": {
                "skipped": {
                    "total_count": 3,
                    "resolved_by_other_suite_count": 3,
                    "unresolved_count": 0,
                }
            },
        },
    }


def rest_report():
    return {
        "status": "ok",
        "source_status_counts": {"implemented": 6, "out-of-scope": 1},
        "summary": {
            "passed": True,
            "source_route_count": 7,
            "in_scope_source_route_count": 6,
            "fixture_matched_source_route_count": 6,
            "live_required_fixture_route_count": 9,
            "live_required_matched_source_route_count": 6,
            "unified_report_fresh": True,
            "unified_required_suite_status": "ok",
            "unified_required_suite_steelsearch_only_breakdown": [],
            "unified_non_required_suite_steelsearch_only_breakdown": [],
            "unified_required_suite_skip_resolution": {
                "total_count": 3,
                "resolved_by_other_suite_count": 3,
                "unresolved_count": 0,
            },
            "unified_required_suite_steelsearch_only_summary": {
                "breakdown_total": 0,
                "effective_delta": 0,
                "effective_total": 0,
                "effective_unexplained_delta": 0,
                "non_required_breakdown_total": 0,
                "raw_delta": 0,
                "raw_total": 0,
            },
        },
    }


def transport_report():
    return {
        "status": "ok",
        "summary": {
            "passed": True,
            "accepted_evidence_action_count": 4,
            "release_parity_evidence_complete": True,
            "release_parity_source_matched_action_count": 4,
            "transport_action_count": 4,
        }
    }


GAP_DOC = """
- `search-compat`: 10 passed, 0 failed, 2 skipped.
- `search-strict`: 8 passed, 0 failed, 1 skipped.
- `search-semantic`: 3 passed, 0 failed, 0 skipped.
  `canonical_equal=11`, `strict_equal=7`, `semantic_equal=3`,
  `steelsearch_only=0`, `known_gap_or_skipped=0`, `failed=0`, `missing=0`;
  `known_gap_or_skipped=0`; all 3 raw skipped cases are covered by other
required suites.
| REST source inventory fixture coverage | `6/6` in-scope source routes matched by fixtures | ok |
| REST live-required source-route mapping | `6/6` in-scope source routes matched by live-required fixture routes, with `9` live-required fixture routes and `0` required-suite Steelsearch-only cases | ok |
| REST source statuses | `implemented=6`, `out-of-scope=1` | ok |
| Transport source inventory | `4` accepted transport evidence rows plus `4/4` source-derived actions with release-parity runtime evidence | ok |
"""


PERFORMANCE_DOC = """
- source REST inventory: 7 total rows, 6 in scope, with 6
  `implemented` and 1 `out-of-scope` rows;
- all repo compatibility fixtures touch 6 of the 6 in-scope source route
  rows and leave 0 in-scope rows without fixture coverage;
- that broader report now touches all 6 in-scope source route rows through
  live-required fixture evidence and leaves 0 in-scope rows outside the current
  live required-suite evidence;
- the broader report still records 3 fixture-classified known gap or skipped
  cases, and all 3 are resolved by dedicated suites in the same unified
  evidence set.
"""


class E2EDocCurrentCountsTest(unittest.TestCase):
    def test_accepts_matching_documents(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC,
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])

    def test_rejects_stale_suite_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC.replace("10 passed", "9 passed"),
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("search-compat.passed: documented 9, report 10", result["errors"])

    def test_rejects_stale_rest_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC,
            performance_doc=PERFORMANCE_DOC.replace("7 total rows", "8 total rows"),
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("REST source_route_count: documented 8, report 7", result["errors"])

    def test_rejects_stale_handoff_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC,
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC.replace("`canonical_equal=11`", "`canonical_equal=10`"),
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("handoff effective canonical_equal: documented 10, report 11", result["errors"])

    def test_rejects_stale_gap_transport_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC.replace("`4` accepted transport", "`3` accepted transport"),
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("gap doc accepted transport evidence rows: documented 3, report 4", result["errors"])

    def test_rejects_stale_gap_rest_live_required_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC.replace("with `9` live-required", "with `8` live-required"),
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "gap doc REST live-required fixture route count: documented 8, report 9",
            result["errors"],
        )

    def test_rejects_stale_gap_rest_status_count(self):
        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest_report(),
            transport_report=transport_report(),
            gap_doc=GAP_DOC.replace("`out-of-scope=1`", "`out-of-scope=2`"),
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("gap doc REST out-of-scope rows: documented 2, report 1", result["errors"])

    def test_rejects_failed_or_stale_input_reports(self):
        rest = rest_report()
        rest["summary"]["unified_report_fresh"] = False
        transport = transport_report()
        transport["summary"]["release_parity_evidence_complete"] = False

        result = checker.validate(
            broad_report={**broad_report(), "status": "failed"},
            rest_report=rest,
            transport_report=transport,
            gap_doc=GAP_DOC,
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn("broad report status is not ok: failed", result["errors"])
        self.assertIn("REST coverage unified report is not fresh", result["errors"])
        self.assertIn("transport release-parity evidence is not complete", result["errors"])

    def test_rejects_required_steelsearch_only_breakdown(self):
        rest = rest_report()
        rest["summary"]["unified_required_suite_steelsearch_only_breakdown"] = [
            {"suite": "search-compat", "steelsearch_only": 1}
        ]
        rest["summary"]["unified_required_suite_steelsearch_only_summary"]["raw_total"] = 1

        result = checker.validate(
            broad_report=broad_report(),
            rest_report=rest,
            transport_report=transport_report(),
            gap_doc=GAP_DOC,
            performance_doc=PERFORMANCE_DOC,
            handoff_doc=GAP_DOC,
        )

        self.assertEqual(result["status"], "failed")
        self.assertIn(
            "REST coverage required-suite Steelsearch-only breakdown is not empty",
            result["errors"],
        )
        self.assertIn(
            "REST coverage Steelsearch-only summary raw_total is not zero: 1",
            result["errors"],
        )


if __name__ == "__main__":
    unittest.main()
