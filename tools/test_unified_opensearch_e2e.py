import importlib.util
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER_PATH = ROOT / "tools" / "run-unified-opensearch-e2e.py"
CHECKER_PATH = ROOT / "tools" / "check-unified-opensearch-e2e-report.py"


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def complete_synthetic_unified_report(skipped, resolved, unresolved):
    covering_cases_by_suite = {}
    for entry in resolved:
        for suite_name in entry.get("covered_by", []):
            covering_cases_by_suite.setdefault(suite_name, set()).add(entry["case"])
    covering_case_count = sum(len(cases) for cases in covering_cases_by_suite.values())
    primary_classification = {
        "strict_equal": 0,
        "canonical_equal": 0,
        "semantic_equal": 0,
        "steelsearch_fail_closed": 0,
        "steelsearch_only": 0,
        "known_gap_or_skipped": len(skipped),
        "failed": 0,
        "missing": 0,
    }
    total_classification = {
        **primary_classification,
        "canonical_equal": covering_case_count,
    }
    semantic_required_suites = ["synthetic", *sorted(covering_cases_by_suite)]
    semantic_report_paths = [
        "synthetic.json",
        *[f"{suite_name}.json" for suite_name in sorted(covering_cases_by_suite)],
    ]
    return {
        "profile": "synthetic",
        "generated_at": 1,
        "status": "ok",
        "route_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
        "semantic_parity": {
            "required_suites": semantic_required_suites,
            "report_paths": semantic_report_paths,
            "status": "ok",
        },
        "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
        "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
        "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
        "coverage_summary": {
            "suite_count": 1 + len(covering_cases_by_suite),
            "required_suite_count": 1 + len(covering_cases_by_suite),
            "reported_suite_count": 1 + len(covering_cases_by_suite),
            "opensearch_compared_suite_count": 1 + len(covering_cases_by_suite),
            "case_classification": total_classification,
            "effective_case_classification": {
                **total_classification,
                "known_gap_or_skipped": len(unresolved),
            },
            "case_gap_resolution": {
                "skipped": {
                    "total_count": len(skipped),
                    "resolved_by_other_suite_count": len(resolved),
                    "unresolved_count": len(unresolved),
                    "resolved": resolved,
                    "unresolved": unresolved,
                }
            },
        },
        "suite_results": [
            {
                "name": "synthetic",
                "area": "search",
                "parity_section": "semantic_parity",
                "required": True,
                "fixture_case_count": len(skipped),
                "status": "ok",
                "summary": {"passed": 0, "failed": 0, "skipped": len(skipped)},
                "has_opensearch_target": True,
                "classification": primary_classification,
                "classification_cases": {
                    "strict_equal": [],
                    "canonical_equal": [],
                    "semantic_equal": [],
                    "steelsearch_fail_closed": [],
                    "steelsearch_only": [],
                    "known_gap_or_skipped": skipped,
                    "failed": [],
                    "missing": [],
                },
                "case_gaps": {
                    "missing": [],
                    "extra": [],
                    "failed": [],
                    "skipped": skipped,
                    "fail_closed": [],
                },
                "report_source": "target",
                "report_path": "synthetic.json",
                "fixture_path": "synthetic-fixture.json",
                "rerun": {"unified_command": "", "direct_command": ""},
            }
        ]
        + [
            {
                "name": suite_name,
                "area": "search",
                "parity_section": "semantic_parity",
                "required": True,
                "fixture_case_count": len(cases),
                "status": "ok",
                "summary": {"passed": len(cases), "failed": 0, "skipped": 0},
                "has_opensearch_target": True,
                "classification": {
                    "strict_equal": 0,
                    "canonical_equal": len(cases),
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 0,
                    "missing": 0,
                },
                "classification_cases": {
                    "strict_equal": [],
                    "canonical_equal": sorted(cases),
                    "semantic_equal": [],
                    "steelsearch_fail_closed": [],
                    "steelsearch_only": [],
                    "known_gap_or_skipped": [],
                    "failed": [],
                    "missing": [],
                },
                "case_gaps": {
                    "missing": [],
                    "extra": [],
                    "failed": [],
                    "skipped": [],
                    "fail_closed": [],
                },
                "passed_cases": sorted(cases),
                "report_source": "target",
                "report_path": f"{suite_name}.json",
                "fixture_path": f"{suite_name}-fixture.json",
                "rerun": {"unified_command": "", "direct_command": ""},
            }
            for suite_name, cases in sorted(covering_cases_by_suite.items())
        ],
    }


class UnifiedOpenSearchE2EReportTests(unittest.TestCase):
    def test_suite_with_missing_fixture_case_is_missing_not_ok(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}, {"name": "uncovered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
                "cases": [{"name": "covered", "status": "passed"}],
            },
        )

        self.assertEqual(result["status"], "missing")
        self.assertEqual(result["classification"]["missing"], 1)
        self.assertEqual(result["classification_cases"]["missing"], ["uncovered"])
        self.assertEqual(result["case_gaps"]["missing"], ["uncovered"])

    def test_suite_with_extra_report_case_is_not_missing_fixture_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_extra_case")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {"name": "covered", "status": "passed"},
                    {"name": "stale-extra", "status": "passed"},
                ],
            },
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["classification"]["missing"], 0)
        self.assertEqual(result["classification"]["canonical_equal"], 1)
        self.assertEqual(result["classification_cases"]["canonical_equal"], ["covered"])
        self.assertEqual(result["case_gaps"]["extra"], ["stale-extra"])

    def test_partial_suite_classifies_reported_subset_without_missing_fixture_cases(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_partial_suite")
        suite = runner.Suite(
            "synthetic-partial",
            "vector-ml",
            "semantic_parity",
            "tools/search_compat.py",
            "unused-fixture.json",
            "partial-report.json",
            needs_opensearch=False,
            allow_partial_report=True,
            default_cases=("covered",),
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}, {"name": "not-in-partial-report"}]},
            {
                "targets": {"steelsearch": "http://steelsearch"},
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
                "cases": [{"name": "covered", "status": "passed"}],
            },
        )

        self.assertEqual(result["status"], "ok")
        self.assertTrue(result["allow_partial_report"])
        self.assertEqual(result["fixture_case_count"], 1)
        self.assertEqual(result["classification"]["missing"], 0)
        self.assertEqual(result["classification"]["steelsearch_only"], 1)
        self.assertEqual(result["case_gaps"]["missing"], [])

    def test_default_cases_limit_superset_report_summary_and_classification(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_default_cases")
        suite = runner.Suite(
            "synthetic-partial",
            "vector-ml",
            "semantic_parity",
            "tools/search_compat.py",
            "unused-fixture.json",
            "partial-report.json",
            needs_opensearch=False,
            allow_partial_report=True,
            default_cases=("included",),
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "included"}, {"name": "excluded"}]},
            {
                "targets": {"steelsearch": "http://steelsearch"},
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {"name": "included", "status": "passed"},
                    {"name": "excluded", "status": "passed"},
                ],
            },
        )

        self.assertEqual(result["fixture_case_count"], 1)
        self.assertEqual(result["summary"]["passed"], 1)
        self.assertEqual(result["classification"]["steelsearch_only"], 1)
        self.assertEqual(result["classification_cases"]["steelsearch_only"], ["included"])
        self.assertEqual(result["case_gaps"]["extra"], ["excluded"])

    def test_suite_treats_fixture_aggregate_case_as_first_class_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_aggregate_case")
        suite = runner.Suite(
            "synthetic-aggregate",
            "vector-ml",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
            needs_opensearch=False,
        )

        result = runner.summarize_suite(
            suite,
            {
                "aggregate_case": {"name": "aggregate"},
                "cases": [{"name": "step"}],
            },
            {
                "targets": {"steelsearch": "http://steelsearch"},
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {"name": "step", "status": "passed"},
                    {"name": "aggregate", "status": "passed"},
                ],
            },
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["case_gaps"]["extra"], [])
        self.assertEqual(result["classification"]["steelsearch_only"], 2)
        self.assertIn("aggregate", result["passed_cases"])

    def test_steelsearch_only_expected_status_classification_separates_supported_and_fail_closed_cases(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_steelsearch_only_status")

        counts = runner.classify_cases(
            [
                {
                    "name": "supported",
                    "comparison": "steelsearch_only",
                    "expected_steelsearch_status": 200,
                },
                {
                    "name": "fail-closed",
                    "comparison": "steelsearch_only",
                    "expected_steelsearch_status": 400,
                },
            ],
            [
                {"name": "supported", "status": "passed"},
                {"name": "fail-closed", "status": "passed"},
            ],
            has_opensearch=False,
        )

        self.assertEqual(counts["steelsearch_only"], 1)
        self.assertEqual(counts["steelsearch_fail_closed"], 1)

    def test_merge_prefers_opensearch_evidence_for_same_passed_case(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_merge_evidence")
        base = {
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "cases": [
                {
                    "name": "isolated",
                    "status": "passed",
                    "targets": {"steelsearch": {"runtime_status": "stateful-route-present"}},
                }
            ],
        }
        partial = {
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "cases": [
                {
                    "name": "isolated",
                    "status": "passed",
                    "targets": {
                        "steelsearch": {"runtime_status": "stateful-route-present"},
                        "opensearch": {"runtime_status": "stateful-route-present"},
                    },
                }
            ],
        }

        merged = runner.merge_missing_case_reports_from_candidates(
            base,
            [
                ((1, 0, 0, 0, 0, 1.0), Path("base.json"), "target", base),
                ((1, 0, 0, 0, 0, 2.0), Path("partial.json"), "target", partial),
            ],
        )

        cases = {case["name"]: case for case in merged["cases"]}
        self.assertIn("opensearch", cases["isolated"]["targets"])

    def test_suite_records_fail_closed_case_names(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_fail_closed_cases")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
            needs_opensearch=False,
        )

        result = runner.summarize_suite(
            suite,
            {
                "cases": [
                    {
                        "name": "supported",
                        "comparison": "steelsearch_only",
                        "expected_steelsearch_status": 200,
                    },
                    {
                        "name": "fail-closed",
                        "comparison": "steelsearch_only",
                        "expected_steelsearch_status": 400,
                    },
                ]
            },
            {
                "targets": {"steelsearch": "http://steelsearch"},
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {"name": "supported", "status": "passed"},
                    {"name": "fail-closed", "status": "passed"},
                ],
            },
        )

        self.assertEqual(result["classification"]["steelsearch_only"], 1)
        self.assertEqual(result["classification"]["steelsearch_fail_closed"], 1)
        self.assertEqual(result["classification_cases"]["steelsearch_only"], ["supported"])
        self.assertEqual(result["classification_cases"]["steelsearch_fail_closed"], ["fail-closed"])
        self.assertEqual(result["case_gaps"]["fail_closed"], ["fail-closed"])

    def test_case_without_opensearch_target_stays_steelsearch_only_in_mixed_report(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_mixed_case_targets")
        suite = runner.Suite(
            "synthetic-mixed",
            "runtime-stateful",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "compared"}, {"name": "steel-only"}]},
            {
                "targets": {
                    "steelsearch": "http://steelsearch",
                    "opensearch": "http://opensearch",
                },
                "summary": {"passed": 2, "failed": 0, "skipped": 0},
                "cases": [
                    {
                        "name": "compared",
                        "status": "passed",
                        "targets": {
                            "steelsearch": {"runtime_status": "stateful-route-present"},
                            "opensearch": {"runtime_status": "stateful-route-present"},
                        },
                    },
                    {
                        "name": "steel-only",
                        "status": "passed",
                        "targets": {
                            "steelsearch": {"runtime_status": "stateful-route-present"},
                        },
                    },
                ],
            },
        )

        self.assertEqual(result["classification_cases"]["canonical_equal"], ["compared"])
        self.assertEqual(result["classification_cases"]["steelsearch_only"], ["steel-only"])
        self.assertFalse(
            runner.report_has_no_reachable_targets(
                {
                    "cases": [
                        {
                            "targets": {
                                "steelsearch": {
                                    "result": {"status": 400},
                                },
                                "opensearch": {
                                    "result": {"status": 400},
                                },
                            }
                        }
                    ]
                }
            )
        )

    def test_build_report_tracks_cross_suite_resolved_skips_separately_from_raw_classification(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_cross_suite_resolution")
        raw_skipped = runner.empty_classification()
        raw_skipped["known_gap_or_skipped"] = 1
        covered = runner.empty_classification()
        covered["steelsearch_only"] = 1

        report = runner.build_report(
            "synthetic",
            [
                {
                    "name": "broad-search",
                    "area": "search",
                    "parity_section": "semantic_parity",
                    "required": True,
                    "status": "ok",
                    "summary": {"passed": 0, "failed": 0, "skipped": 1},
                    "classification": raw_skipped,
                    "case_gaps": {
                        "missing": [],
                        "extra": [],
                        "failed": [],
                        "skipped": ["covered-case"],
                    },
                    "passed_cases": [],
                    "report_source": "target",
                    "report_path": "broad-search.json",
                    "has_opensearch_target": True,
                },
                {
                    "name": "focused-surface",
                    "area": "search",
                    "parity_section": "semantic_parity",
                    "required": True,
                    "status": "ok",
                    "summary": {"passed": 1, "failed": 0, "skipped": 0},
                    "classification": covered,
                    "case_gaps": {
                        "missing": [],
                        "extra": [],
                        "failed": [],
                        "skipped": [],
                    },
                    "passed_cases": ["covered-case"],
                    "report_source": "target",
                    "report_path": "focused-surface.json",
                    "has_opensearch_target": False,
                },
            ],
        )

        self.assertEqual(report["coverage_summary"]["case_classification"]["known_gap_or_skipped"], 1)
        self.assertEqual(
            report["coverage_summary"]["effective_case_classification"]["known_gap_or_skipped"],
            0,
        )
        self.assertEqual(
            report["coverage_summary"]["case_gap_resolution"]["skipped"]["resolved_by_other_suite_count"],
            1,
        )
        self.assertEqual(
            report["coverage_summary"]["case_gap_resolution"]["skipped"]["unresolved_count"],
            0,
        )

    def test_suite_recomputes_failed_count_from_cases_when_summary_lies(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_summary_drift")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
                "cases": [{"name": "covered", "status": "failed"}],
            },
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["summary"]["passed"], 0)
        self.assertEqual(result["summary"]["failed"], 1)
        self.assertEqual(
            result["summary_drift"],
            {
                "passed": {"reported": 1, "recomputed": 0},
                "failed": {"reported": 0, "recomputed": 1},
            },
        )

    def test_suite_ignores_extra_failed_cases_for_fixture_summary_status(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_extra_case_summary")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 1, "failed": 1, "skipped": 0},
                "cases": [
                    {"name": "covered", "status": "passed"},
                    {"name": "stale-extra", "status": "failed"},
                ],
            },
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["summary"]["passed"], 1)
        self.assertEqual(result["summary"]["failed"], 0)
        self.assertEqual(result["summary_drift"], {})
        self.assertEqual(result["case_gaps"]["extra"], ["stale-extra"])

    def test_suite_treats_unknown_case_status_as_failed_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_unknown_status")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            None,
            "unused-fixture.json",
            "unused-report.json",
        )

        result = runner.summarize_suite(
            suite,
            {"cases": [{"name": "covered"}]},
            {
                "targets": {"steelsearch": "http://steelsearch", "opensearch": "http://opensearch"},
                "summary": {"passed": 0, "failed": 0, "skipped": 0},
                "cases": [{"name": "covered", "status": "unknown"}],
            },
        )

        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["classification"]["failed"], 1)
        self.assertEqual(result["case_gaps"]["failed"], ["covered"])

    def test_checker_rejects_required_suite_with_missing_case_without_allow_missing(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_report")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "missing",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "missing",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 1,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 0,
                    "missing": 1,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "missing",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 1,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 0,
                        "failed": 0,
                        "missing": 1,
                    },
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("report has missing required suite evidence", errors)
        self.assertIn("synthetic: missing fixture case evidence", errors)

    def test_checker_rejects_incomplete_suite_result_shape(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_incomplete_suite")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 0,
                "opensearch_compared_suite_count": 0,
                "case_classification": {},
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "ok",
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("synthetic: missing suite field [summary]", errors)
        self.assertIn("synthetic: missing suite field [case_gaps]", errors)
        self.assertIn("synthetic: missing suite field [report_source]", errors)
        self.assertIn("synthetic: missing suite field [rerun]", errors)

    def test_checker_rejects_malformed_suite_result_shape(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_malformed_suite")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 1,
                    "canonical_equal": 0,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 0,
                    "missing": 0,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "area": "",
                    "parity_section": "unknown",
                    "required": "yes",
                    "fixture_case_count": -1,
                    "status": "ok",
                    "summary": {"passed": True, "failed": 0, "skipped": 0},
                    "has_opensearch_target": "yes",
                    "classification": {
                        "strict_equal": 1,
                        "canonical_equal": 0,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 0,
                        "failed": 0,
                        "missing": 0,
                    },
                    "case_gaps": {
                        "missing": [],
                        "extra": [],
                        "failed": [],
                        "skipped": "no",
                        "fail_closed": [],
                    },
                    "report_source": "handwritten",
                    "report_path": "",
                    "fixture_path": "",
                    "rerun": {"unified_command": [], "direct_command": ""},
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("synthetic: invalid parity_section [unknown]", errors)
        self.assertIn("synthetic: required must be boolean", errors)
        self.assertIn("synthetic: fixture_case_count must be a non-negative integer", errors)
        self.assertIn("synthetic: summary.passed must be a non-negative integer", errors)
        self.assertIn("synthetic: case_gaps.skipped must be a list", errors)
        self.assertIn("synthetic: rerun.unified_command must be a string", errors)

    def test_checker_rejects_classification_case_name_drift(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_classification_cases")
        report = complete_synthetic_unified_report(
            skipped=["skipped-case"],
            resolved=[],
            unresolved=["skipped-case"],
        )
        report["suite_results"][0]["classification_cases"]["known_gap_or_skipped"] = []

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn(
            "synthetic: classification_cases.known_gap_or_skipped/classification.known_gap_or_skipped drift",
            errors,
        )

    def test_checker_rejects_required_skips_when_requested(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_no_skips")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "semantic_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 0,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 1,
                    "failed": 0,
                    "missing": 0,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "ok",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 0,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 1,
                        "failed": 0,
                        "missing": 0,
                    },
                }
            ],
        }

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_skips=True,
        )

        self.assertIn("synthetic: skipped required fixture cases", errors)

    def test_checker_accepts_resolved_skips_when_unresolved_gate_requested(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_resolved_skips")
        report = complete_synthetic_unified_report(
            skipped=["covered-case"],
            resolved=[{"suite": "synthetic", "case": "covered-case", "covered_by": ["focused"]}],
            unresolved=[],
        )

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_unresolved_skips=True,
        )

        self.assertEqual(errors, [])

    def test_checker_rejects_unresolved_skips_when_requested(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_unresolved_skips")
        report = complete_synthetic_unified_report(
            skipped=["uncovered-case"],
            resolved=[],
            unresolved=[{"suite": "synthetic", "case": "uncovered-case"}],
        )

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_unresolved_skips=True,
        )

        self.assertIn("unresolved skipped fixture cases: synthetic:uncovered-case", errors)

    def test_checker_rejects_resolved_skip_when_covering_suite_did_not_pass_case(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_bad_skip_cover")
        report = complete_synthetic_unified_report(
            skipped=["covered-case"],
            resolved=[{"suite": "synthetic", "case": "covered-case", "covered_by": ["focused"]}],
            unresolved=[],
        )
        report["suite_results"][1]["passed_cases"] = []

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_unresolved_skips=True,
        )

        self.assertIn(
            "synthetic:covered-case: covering suite focused did not pass the case",
            errors,
        )

    def test_checker_rejects_skip_resolution_count_drift(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_skip_count_drift")
        report = complete_synthetic_unified_report(
            skipped=["covered-case"],
            resolved=[{"suite": "synthetic", "case": "covered-case", "covered_by": ["focused"]}],
            unresolved=[],
        )
        report["coverage_summary"]["case_gap_resolution"]["skipped"]["resolved_by_other_suite_count"] = 0

        errors = checker.validate_report(
            report,
            allow_missing=False,
            require_no_unresolved_skips=True,
        )

        self.assertIn(
            "case_gap_resolution.skipped.resolved_by_other_suite_count drift",
            errors,
        )

    def test_checker_accepts_fixture_declared_steelsearch_only_case(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_steel_only_fixture")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            fixture = Path(temp_dir_value) / "fixture.json"
            fixture.write_text(
                """
{
  "cases": [
    {
      "name": "steel-only",
      "comparison": "steelsearch_only",
      "expected_steelsearch_status": 200
    }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            report = complete_synthetic_unified_report([], [], [])
            suite = report["suite_results"][0]
            suite["fixture_path"] = str(fixture)
            suite["fixture_case_count"] = 1
            suite["summary"] = {"passed": 1, "failed": 0, "skipped": 0}
            suite["classification"]["steelsearch_only"] = 1
            suite["classification_cases"]["steelsearch_only"] = ["steel-only"]
            suite["passed_cases"] = ["steel-only"]
            report["coverage_summary"]["case_classification"]["steelsearch_only"] = 1
            report["coverage_summary"]["effective_case_classification"]["steelsearch_only"] = 1

            errors = checker.validate_report(report, allow_missing=False)

        self.assertEqual(errors, [])

    def test_checker_rejects_steelsearch_only_case_not_declared_by_fixture(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_bad_steel_only_fixture")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            fixture = Path(temp_dir_value) / "fixture.json"
            fixture.write_text(
                """
{
  "cases": [
    { "name": "steel-only" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            report = complete_synthetic_unified_report([], [], [])
            suite = report["suite_results"][0]
            suite["fixture_path"] = str(fixture)
            suite["fixture_case_count"] = 1
            suite["summary"] = {"passed": 1, "failed": 0, "skipped": 0}
            suite["classification"]["steelsearch_only"] = 1
            suite["classification_cases"]["steelsearch_only"] = ["steel-only"]
            suite["passed_cases"] = ["steel-only"]
            report["coverage_summary"]["case_classification"]["steelsearch_only"] = 1
            report["coverage_summary"]["effective_case_classification"]["steelsearch_only"] = 1

            errors = checker.validate_report(report, allow_missing=False)

        self.assertIn(
            "synthetic: steelsearch_only case steel-only is not fixture-declared steelsearch_only",
            errors,
        )

    def test_checker_rejects_required_suite_failure_even_if_top_level_is_ok(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_failed_suite")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 0,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 1,
                    "missing": 0,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "failed",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "summary": {"passed": 0, "failed": 1, "skipped": 0},
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 0,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 0,
                        "failed": 1,
                        "missing": 0,
                    },
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("synthetic: required suite status is failed", errors)
        self.assertIn("synthetic: required suite has failed cases", errors)
        self.assertIn("synthetic: failed fixture case evidence", errors)

    def test_checker_can_validate_blocked_report_shape_when_allowed(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_allow_blocked")
        report = complete_synthetic_unified_report([], [], [])
        report["status"] = "blocked"
        report["security_parity"]["status"] = "blocked"

        strict_errors = checker.validate_report(report, allow_missing=False)
        allowed_errors = checker.validate_report(
            report,
            allow_missing=False,
            allow_blocked=True,
        )

        self.assertIn("report has blocked or failed suite evidence", strict_errors)
        self.assertEqual(allowed_errors, [])

    def test_checker_can_require_nonempty_parity_sections(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_required_sections")
        report = complete_synthetic_unified_report([], [], [])

        errors = checker.validate_report(
            report,
            allow_missing=False,
            required_nonempty_sections={"semantic_parity", "distributed_parity"},
        )

        self.assertIn("distributed_parity: no required suites", errors)
        self.assertNotIn("semantic_parity: no required suites", errors)

    def test_checker_rejects_parity_section_required_suite_drift(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_section_suite_drift")
        report = complete_synthetic_unified_report([], [], [])
        report["semantic_parity"]["required_suites"] = []

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("semantic_parity: required_suites drift from suite_results", errors)

    def test_checker_rejects_parity_section_report_path_drift(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_section_path_drift")
        report = complete_synthetic_unified_report([], [], [])
        report["semantic_parity"]["report_paths"] = []

        errors = checker.validate_report(report, allow_missing=False)

        self.assertIn("semantic_parity: report_paths drift from suite_results", errors)

    def test_checker_report_freshness_rejects_stale_report(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_freshness")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            path = Path(temp_dir_value) / "unified.json"
            path.write_text("{}", encoding="utf-8")
            stale_mtime = time.time() - 120.0
            os.utime(path, (stale_mtime, stale_mtime))

            freshness = checker.report_fresh(path, 60.0)

        self.assertFalse(freshness["fresh"])
        self.assertIn("report is stale", freshness["reason"])
        self.assertEqual(freshness["max_age_seconds"], 60.0)

    def test_checker_rejects_suite_summary_drift(self):
        checker = load_module(CHECKER_PATH, "check_unified_opensearch_e2e_summary_drift")
        report = {
            "profile": "synthetic",
            "generated_at": 1,
            "status": "ok",
            "route_parity": {
                "required_suites": ["synthetic"],
                "report_paths": ["synthetic.json"],
                "status": "ok",
            },
            "semantic_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "durability_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "security_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "distributed_parity": {"required_suites": [], "report_paths": [], "status": "ok"},
            "coverage_summary": {
                "suite_count": 1,
                "required_suite_count": 1,
                "reported_suite_count": 1,
                "opensearch_compared_suite_count": 1,
                "case_classification": {
                    "strict_equal": 0,
                    "canonical_equal": 1,
                    "semantic_equal": 0,
                    "steelsearch_fail_closed": 0,
                    "steelsearch_only": 0,
                    "known_gap_or_skipped": 0,
                    "failed": 0,
                    "missing": 0,
                },
            },
            "suite_results": [
                {
                    "name": "synthetic",
                    "required": True,
                    "status": "ok",
                    "report_source": "target",
                    "has_opensearch_target": True,
                    "summary": {"passed": 1, "failed": 0, "skipped": 0},
                    "summary_drift": {"passed": {"reported": 2, "recomputed": 1}},
                    "classification": {
                        "strict_equal": 0,
                        "canonical_equal": 1,
                        "semantic_equal": 0,
                        "steelsearch_fail_closed": 0,
                        "steelsearch_only": 0,
                        "known_gap_or_skipped": 0,
                        "failed": 0,
                        "missing": 0,
                    },
                }
            ],
        }

        errors = checker.validate_report(report, allow_missing=False)

        self.assertTrue(
            any(error.startswith("synthetic: suite summary drift") for error in errors)
        )

    def test_rerun_commands_include_missing_cases(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_rerun")
        suite = runner.Suite(
            "synthetic",
            "search",
            "semantic_parity",
            "tools/search_compat.py",
            "tools/fixtures/search-compat.json",
            "synthetic-report.json",
            output_arg="--report",
        )

        commands = runner.suite_rerun_commands(
            suite,
            Path("target/e2e"),
            {"missing": ["case-a", "case-b"]},
        )

        self.assertIn("--case case-a --case case-b", commands["unified_command"])
        self.assertIn("--case case-a --case case-b", commands["direct_command"])

    def test_security_harness_rerun_command_uses_security_entrypoint_without_case_filter(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_security_rerun")
        suite = runner.Suite(
            "security-authz",
            "security",
            "security_parity",
            "tools/run-security-compat-harness.sh",
            "tools/fixtures/security-authz-compat.json",
            "security-authz-compat-report.json",
            required=False,
            needs_opensearch=False,
            output_arg="--report",
            runner_kind="security-harness",
        )

        commands = runner.suite_rerun_commands(
            suite,
            Path("target/e2e"),
            {"missing": ["case-a"]},
        )

        self.assertIn("tools/run-security-compat-harness.sh", commands["direct_command"])
        self.assertIn("--report target/e2e/security-authz-compat-report.json", commands["direct_command"])
        self.assertNotIn("--opensearch-url", commands["unified_command"])
        self.assertNotIn("--opensearch-url", commands["direct_command"])
        self.assertNotIn("--case", commands["unified_command"])
        self.assertNotIn("--case", commands["direct_command"])

    def test_security_authz_suite_is_required_for_broad_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_security_required")
        suites = {suite.name: suite for suite in runner.SUITES}

        self.assertIn("security-authz", suites)
        self.assertTrue(suites["security-authz"].required)
        self.assertEqual(suites["security-authz"].parity_section, "security_parity")

    def test_security_harness_live_command_uses_shell_harness_without_opensearch_by_default(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_security_command")
        suite = runner.Suite(
            "security-authz",
            "security",
            "security_parity",
            "tools/run-security-compat-harness.sh",
            "tools/fixtures/security-authz-compat.json",
            "security-authz-compat-report.json",
            required=False,
            needs_opensearch=False,
            output_arg="--report",
            runner_kind="security-harness",
        )
        args = type(
            "Args",
            (),
            {
                "steelsearch_url": "https://steelsearch.example/",
                "opensearch_url": "https://opensearch.example/",
            },
        )()

        command = runner.suite_run_command(
            suite,
            Path("target/e2e"),
            args,
            Path("target/e2e/security-authz-compat-report.json"),
        )

        self.assertEqual(command[0], str(ROOT / "tools/run-security-compat-harness.sh"))
        self.assertNotIn(sys.executable, command[:1])
        self.assertNotIn("--opensearch-url", command)
        self.assertIn("--report-dir", command)

    def test_optional_opensearch_suite_receives_url_without_requiring_it(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_optional_opensearch")
        suites = {suite.name: suite for suite in runner.SUITES}
        args = type(
            "Args",
            (),
            {
                "steelsearch_url": "http://steelsearch.example/",
                "opensearch_url": "http://opensearch.example/",
                "timeout": 7.0,
            },
        )()

        for suite_name, report_name in (
            ("ml-model-surface", "ml-model-surface-compat-report.json"),
            ("knn-plugin-surface", "knn-plugin-compat-report.json"),
            ("vector-search-native-surface", "vector-search-native-surface-report.json"),
        ):
            suite = suites[suite_name]
            command = runner.suite_run_command(
                suite,
                Path("target/e2e"),
                args,
                Path(f"target/e2e/{report_name}"),
            )

            self.assertFalse(suite.needs_opensearch)
            self.assertTrue(suite.accepts_optional_opensearch)
            self.assertIn("--opensearch-url", command)
            self.assertIn("http://opensearch.example", command)

    def test_multi_node_write_path_rerun_command_uses_node_urls_without_case_filter(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_write_path_rerun")
        suite = runner.Suite(
            "multi-node-write-path",
            "distributed",
            "distributed_parity",
            "tools/multi_node_write_path_integration.py",
            "tools/fixtures/multi-node-write-path.json",
            "multi-node-write-path-report.json",
            required=False,
            needs_opensearch=False,
            output_arg="--output",
            runner_kind="multi-node",
        )

        commands = runner.suite_rerun_commands(
            suite,
            Path("target/e2e"),
            {"missing": ["case-a"]},
        )

        self.assertIn("--node-a-url ${STEELSEARCH_NODE_A_URL}", commands["unified_command"])
        self.assertIn("--node-b-url ${STEELSEARCH_NODE_B_URL}", commands["unified_command"])
        self.assertIn("tools/multi_node_write_path_integration.py", commands["direct_command"])
        self.assertIn("--output target/e2e/multi-node-write-path-report.json", commands["direct_command"])
        self.assertNotIn("--case", commands["unified_command"])
        self.assertNotIn("--case", commands["direct_command"])

    def test_multi_node_write_path_live_command_uses_python_runner_and_node_urls(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_write_path_command")
        suite = runner.Suite(
            "multi-node-write-path",
            "distributed",
            "distributed_parity",
            "tools/multi_node_write_path_integration.py",
            "tools/fixtures/multi-node-write-path.json",
            "multi-node-write-path-report.json",
            required=False,
            needs_opensearch=False,
            output_arg="--output",
            runner_kind="multi-node",
        )
        args = type(
            "Args",
            (),
            {
                "steelsearch_url": "http://node-a-from-steelsearch.example/",
                "opensearch_url": None,
                "node_a_url": "http://node-a.example/",
                "node_b_url": "http://node-b.example/",
                "timeout": 7.0,
            },
        )()

        command = runner.suite_run_command(
            suite,
            Path("target/e2e"),
            args,
            Path("target/e2e/multi-node-write-path-report.json"),
        )

        self.assertEqual(command[0], sys.executable)
        self.assertIn(str(ROOT / "tools/multi_node_write_path_integration.py"), command)
        self.assertIn("--node-a-url", command)
        self.assertIn("http://node-a.example", command)
        self.assertIn("--node-b-url", command)
        self.assertIn("http://node-b.example", command)
        self.assertNotIn("--opensearch-url", command)

    def test_optional_failed_suite_does_not_block_section_status(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_optional_section")
        suites = [
            {
                "name": "required-distributed",
                "parity_section": "distributed_parity",
                "required": True,
                "report_source": "output-dir",
                "report_path": "target/required.json",
                "status": "ok",
                "summary": {"passed": 1, "failed": 0, "skipped": 0},
                "classification": runner.empty_classification(),
                "has_opensearch_target": False,
            },
            {
                "name": "optional-distributed",
                "parity_section": "distributed_parity",
                "required": False,
                "report_source": "output-dir",
                "report_path": "target/optional.json",
                "status": "blocked",
                "summary": {"passed": 0, "failed": 0, "skipped": 0},
                "classification": runner.empty_classification(),
                "has_opensearch_target": False,
            },
        ]

        section = runner.section_summary("distributed_parity", suites)

        self.assertEqual(section["status"], "ok")
        self.assertEqual(section["failed_suites"], [])

    def test_multi_node_transport_admin_rerun_command_uses_node_urls_without_case_filter(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_transport_admin_rerun")
        suite = runner.Suite(
            "multi-node-transport-admin",
            "distributed",
            "distributed_parity",
            "tools/multi_node_transport_admin_integration.py",
            "tools/fixtures/multi-node-transport-admin.json",
            "multi-node-transport-admin-report.json",
            needs_opensearch=False,
            output_arg="--output",
            runner_kind="multi-node",
        )

        commands = runner.suite_rerun_commands(
            suite,
            Path("target/e2e"),
            {"missing": ["case-a"]},
        )

        self.assertIn("--node-a-url ${STEELSEARCH_NODE_A_URL}", commands["unified_command"])
        self.assertIn("--node-b-url ${STEELSEARCH_NODE_B_URL}", commands["unified_command"])
        self.assertIn("tools/multi_node_transport_admin_integration.py", commands["direct_command"])
        self.assertIn("--output target/e2e/multi-node-transport-admin-report.json", commands["direct_command"])
        self.assertNotIn("--case", commands["unified_command"])
        self.assertNotIn("--case", commands["direct_command"])

    def test_merge_case_reports_preserves_existing_cases_and_recomputes_summary(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_merge")
        base = {
            "name": "synthetic",
            "fixture": "/tmp/fixture.json",
            "targets": {"steelsearch": "old", "opensearch": "old"},
            "summary": {"passed": 1, "failed": 1, "skipped": 0},
            "cases": [
                {"name": "existing-pass", "status": "passed", "area": "search"},
                {"name": "rerun-me", "status": "failed", "area": "search"},
            ],
        }
        partial = {
            "targets": {"steelsearch": "new", "opensearch": "new"},
            "summary": {"passed": 1, "failed": 0, "skipped": 0},
            "cases": [
                {"name": "rerun-me", "status": "passed", "area": "search"},
            ],
        }

        merged = runner.merge_case_reports(base, partial)

        cases = {case["name"]: case for case in merged["cases"]}
        self.assertEqual(cases["existing-pass"]["status"], "passed")
        self.assertEqual(cases["rerun-me"]["status"], "passed")
        self.assertEqual(merged["targets"], {"steelsearch": "new", "opensearch": "new"})
        self.assertEqual(merged["summary"]["passed"], 2)
        self.assertEqual(merged["summary"]["failed"], 0)
        self.assertEqual(merged["summary"]["skipped"], 0)
        self.assertEqual(merged["summary"]["by_area"]["search"]["passed"], 2)

    def test_load_best_report_prefers_complete_passing_report_over_newer_failed_report(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_best_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" },
    { "name": "case-b" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "nested"
            recursive_dir.mkdir(parents=True)
            passing_report = output_dir / "synthetic-report.json"
            failed_report = recursive_dir / "synthetic-report.json"
            passing_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 2, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" },
    { "name": "case-b", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            time.sleep(0.01)
            failed_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 1, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" },
    { "name": "case-b", "status": "failed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, passing_report)
            self.assertEqual(source, "output-dir")
            self.assertIsNone(unusable)
            self.assertEqual(report["summary"]["failed"], 0)

    def test_load_best_report_merges_complementary_partial_reports(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_merged_partials")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" },
    { "name": "case-b" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "nested"
            recursive_dir.mkdir(parents=True)
            first_report = output_dir / "synthetic-report.json"
            second_report = recursive_dir / "synthetic-report.json"
            first_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            second_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-b", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertIn(path, {first_report, second_report})
            self.assertTrue(source.endswith("+merged"))
            self.assertIsNone(unusable)
            self.assertEqual({case["name"] for case in report["cases"]}, {"case-a", "case-b"})
            self.assertEqual(report["summary"]["passed"], 2)
            self.assertEqual(report["summary"]["failed"], 0)

    def test_load_best_report_replaces_failed_case_with_passing_partial_evidence(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_replaces_failed_case")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" },
    { "name": "case-b" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "focused"
            recursive_dir.mkdir(parents=True)
            broad_report = output_dir / "synthetic-report.json"
            focused_report = recursive_dir / "synthetic-report.json"
            broad_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 1, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" },
    { "name": "case-b", "status": "failed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            focused_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-b", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                _path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(source, "output-dir+merged")
            self.assertIsNone(unusable)
            cases = {case["name"]: case for case in report["cases"]}
            self.assertEqual(cases["case-b"]["status"], "passed")
            self.assertEqual(report["summary"]["passed"], 2)
            self.assertEqual(report["summary"]["failed"], 0)

    def test_search_compat_suite_collects_generic_harness_report_name_by_fixture(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_generic_search_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "search-strict-compat.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "strict-case" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            recursive_dir = temp_dir / "target" / "strict-harness" / "compare"
            recursive_dir.mkdir(parents=True)
            generic_report = recursive_dir / "search-compat-report.json"
            generic_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "strict-case", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    ("search-strict-compat-report.json", "search-compat-report.json"),
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, generic_report)
            self.assertEqual(source, "target-recursive")
            self.assertIsNone(unusable)
            self.assertEqual(report["summary"]["passed"], 1)

    def test_opensearch_suite_ignores_steelsearch_only_reports(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_requires_opensearch")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "search-compat.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            steel_only = temp_dir / "target" / "search-compat-report.json"
            steel_only.parent.mkdir(parents=True)
            steel_only.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            compared_dir = temp_dir / "target" / "compare"
            compared_dir.mkdir()
            compared = compared_dir / "search-compat-report.json"
            compared.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "search-compat-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                    require_opensearch_target=True,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, compared)
            self.assertEqual(source, "target-recursive")
            self.assertIsNone(unusable)
            self.assertIn("opensearch", report["targets"])

    def test_partial_search_suite_does_not_collect_generic_search_report_name(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_partial_search_report")
        suite = runner.Suite(
            "synthetic-partial",
            "vector-ml",
            "semantic_parity",
            "tools/search_compat.py",
            "tools/fixtures/search-compat.json",
            "partial-search-report.json",
            allow_partial_report=True,
        )

        self.assertEqual(
            runner.report_names_for_suite(suite),
            ("partial-search-report.json",),
        )

    def test_report_names_for_suite_includes_explicit_aliases(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_report_aliases")
        suite = runner.Suite(
            "synthetic-strict",
            "search",
            "semantic_parity",
            "tools/search_compat.py",
            "tools/fixtures/search-strict-compat.json",
            "search-strict-compat-report.json",
            output_arg="--report",
            report_aliases=("quoted-phrase-report.json", "query-string-family-report.json"),
        )

        self.assertEqual(
            runner.report_names_for_suite(suite),
            (
                "search-strict-compat-report.json",
                "quoted-phrase-report.json",
                "query-string-family-report.json",
                "search-compat-report.json",
            ),
        )

    def test_load_best_report_rejects_stale_complete_report_when_age_gate_is_set(self):
        runner = load_module(RUNNER_PATH, "run_unified_opensearch_e2e_stale_report")
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            fixture_path = temp_dir / "fixture.json"
            fixture_path.write_text(
                """
{
  "cases": [
    { "name": "case-a" }
  ]
}
""".strip(),
                encoding="utf-8",
            )
            output_dir = temp_dir / "out"
            output_dir.mkdir()
            stale_report = output_dir / "synthetic-report.json"
            stale_report.write_text(
                """
{
  "fixture": "__FIXTURE__",
  "targets": { "steelsearch": "s", "opensearch": "o" },
  "summary": { "passed": 1, "failed": 0, "skipped": 0 },
  "cases": [
    { "name": "case-a", "status": "passed" }
  ]
}
""".replace("__FIXTURE__", str(fixture_path)),
                encoding="utf-8",
            )
            stale_mtime = time.time() - 120.0
            os.utime(stale_report, (stale_mtime, stale_mtime))

            previous_root = runner.ROOT
            runner.ROOT = temp_dir
            try:
                path, source, report, unusable = runner.load_best_report(
                    "synthetic-report.json",
                    fixture_path,
                    output_dir,
                    recursive_target_scan=True,
                    max_report_age_seconds=60.0,
                )
                result = runner.collect_suite(
                    runner.Suite(
                        "synthetic",
                        "search",
                        "semantic_parity",
                        None,
                        str(fixture_path),
                        "synthetic-report.json",
                    ),
                    output_dir,
                    max_report_age_seconds=60.0,
                )
            finally:
                runner.ROOT = previous_root

            self.assertEqual(path, stale_report)
            self.assertIsNone(source)
            self.assertIsNone(report)
            self.assertIsNone(unusable)
            self.assertEqual(result["status"], "missing")
            self.assertEqual(result["report_source"], "missing")
            self.assertIn("max_report_age_seconds=60", result["note"])


if __name__ == "__main__":
    unittest.main()
