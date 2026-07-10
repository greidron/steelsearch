import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "tools" / "generate-benchmark-evidence.py"
CHECKER_PATH = ROOT / "tools" / "check-benchmark-evidence.py"


def load_benchmark_module():
    module_name = "generate_benchmark_evidence"
    spec = importlib.util.spec_from_file_location(module_name, BENCHMARK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def load_checker_module():
    module_name = "check_benchmark_evidence"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class BenchmarkEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.benchmark = load_benchmark_module()
        self.checker = load_checker_module()

    def test_generate_report_accepts_complete_benchmark_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source = Path(temp_dir_value) / "benchmarks.jsonl"
            source.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS), encoding="utf-8")

            report, records = self.benchmark.generate_report(
                Path(temp_dir_value),
                source_jsonl=source,
            )

            self.assertTrue(report["ready"])
            self.assertTrue(report["summary"]["passed"])
            self.assertEqual(report["summary"]["error_count"], 0)
            self.assertEqual(len(records), len(self.benchmark.EXPECTED_BENCHMARKS))

    def test_generate_report_rejects_missing_expected_benchmark(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            source = Path(temp_dir_value) / "benchmarks.jsonl"
            source.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS[:-1]), encoding="utf-8")

            report, _ = self.benchmark.generate_report(
                Path(temp_dir_value),
                source_jsonl=source,
            )

            self.assertFalse(report["ready"])
            self.assertTrue(
                any("nested_child_index_search" in blocker for blocker in report["blockers"])
            )

    def test_cli_writes_jsonl_and_report_from_source_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "benchmarks.jsonl"
            output = temp_dir / "out" / "deterministic-baselines.jsonl"
            report_path = temp_dir / "out" / "benchmark-report.json"
            source.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS), encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(BENCHMARK_PATH),
                    "--source-jsonl",
                    str(source),
                    "--output",
                    str(output),
                    "--report",
                    str(report_path),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["summary"]["passed"])

    def test_checker_accepts_matching_jsonl_and_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            jsonl = temp_dir / "benchmarks.jsonl"
            report_path = temp_dir / "benchmark-report.json"
            jsonl.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS), encoding="utf-8")
            report, _records = self.benchmark.generate_report(
                temp_dir,
                source_jsonl=jsonl,
            )
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = self.checker.validate_benchmark_evidence(jsonl, report_path)

            self.assertTrue(result["summary"]["passed"])
            self.assertEqual(result["summary"]["benchmark_count"], 9)
            self.assertEqual(result["errors"], [])

    def test_checker_rejects_report_record_count_drift(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            jsonl = temp_dir / "benchmarks.jsonl"
            report_path = temp_dir / "benchmark-report.json"
            jsonl.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS), encoding="utf-8")
            report, _records = self.benchmark.generate_report(
                temp_dir,
                source_jsonl=jsonl,
            )
            report["summary"]["record_count"] = 1
            report_path.write_text(json.dumps(report), encoding="utf-8")

            result = self.checker.validate_benchmark_evidence(jsonl, report_path)

            self.assertFalse(result["summary"]["passed"])
            self.assertIn("benchmark report summary.record_count drift", result["errors"])

    def test_checker_rejects_stale_jsonl(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            jsonl = temp_dir / "benchmarks.jsonl"
            report_path = temp_dir / "benchmark-report.json"
            jsonl.write_text(valid_jsonl(self.benchmark.EXPECTED_BENCHMARKS), encoding="utf-8")
            report, _records = self.benchmark.generate_report(
                temp_dir,
                source_jsonl=jsonl,
            )
            report_path.write_text(json.dumps(report), encoding="utf-8")
            stale_mtime = 1
            jsonl.touch()
            report_path.touch()

            os.utime(jsonl, (stale_mtime, stale_mtime))

            result = self.checker.validate_benchmark_evidence(
                jsonl,
                report_path,
                max_age_seconds=1,
            )

            self.assertFalse(result["summary"]["passed"])
            self.assertTrue(any("benchmark JSONL is stale" in error for error in result["errors"]))


def valid_jsonl(names):
    return "".join(
        json.dumps(
            {
                "benchmark": name,
                "operations": 2,
                "elapsed_nanos": 100,
                "nanos_per_operation": 50,
            }
        )
        + "\n"
        for name in names
    )


if __name__ == "__main__":
    unittest.main()
