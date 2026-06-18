import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_PATH = ROOT / "tools" / "generate-benchmark-evidence.py"


def load_benchmark_module():
    module_name = "generate_benchmark_evidence"
    spec = importlib.util.spec_from_file_location(module_name, BENCHMARK_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class BenchmarkEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.benchmark = load_benchmark_module()

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
