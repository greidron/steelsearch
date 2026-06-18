import os
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReplacementGateScriptTests(unittest.TestCase):
    def run_command(self, *args, env=None):
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)
        return subprocess.run(
            args,
            cwd=ROOT,
            env=merged_env,
            text=True,
            capture_output=True,
            check=False,
        )

    def test_development_replacement_gate_dry_run_sequence(self):
        result = self.run_command("./tools/run-development-replacement-gate.sh", "--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip().splitlines(),
            [
                "+ cargo build -p os-node --features standalone-runtime --bin steelsearch",
                "+ cargo test --workspace --no-run",
                "+ tools/run-steelsearch-smoke.sh",
                "+ tools/run-daemon-backed-search-compat.sh",
                "+ tools/run-cargo-test-group.sh unit",
                "+ tools/run-cargo-test-group.sh daemon-integration",
                "+ tools/run-cargo-test-group.sh migration",
                "+ tools/run-cargo-test-group.sh k-nn",
                "+ tools/run-cargo-test-group.sh model-serving",
                "+ tools/run-cargo-test-group.sh multi-node",
            ],
        )

    def test_development_replacement_gate_rejects_unknown_args(self):
        result = self.run_command("./tools/run-development-replacement-gate.sh", "--bogus")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)

    def test_daemon_backed_search_compat_dry_run_forwards_report_path(self):
        result = self.run_command(
            "./tools/run-daemon-backed-search-compat.sh",
            "--dry-run",
            "--report",
            "target/test-search-compat-report.json",
            env={"STEELSEARCH_URL": "http://127.0.0.1:9200"},
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(
            "+ export STEELSEARCH_URL=http://127.0.0.1:9200",
            result.stdout,
        )
        self.assertIn(
            "+ tools/run-search-compat.sh --report target/test-search-compat-report.json",
            result.stdout,
        )

    def test_attach_release_readiness_evidence_writes_startup_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            readiness = temp_dir / "readiness.json"
            benchmark = temp_dir / "benchmark.jsonl"
            load = temp_dir / "load.json"
            comparison = temp_dir / "comparison.json"
            chaos = temp_dir / "chaos.json"
            packaging = temp_dir / "packaging.json"
            rolling = temp_dir / "rolling.json"
            release_readiness = temp_dir / "release-readiness.json"

            readiness.write_text(
                json.dumps(
                    {
                        "ready": True,
                        "categories": {
                            "security": {"ready": True, "blockers": []},
                        },
                    }
                ),
                encoding="utf-8",
            )
            benchmark.write_text(json.dumps({"benchmark": "lexical"}) + "\n", encoding="utf-8")
            for path in [load, comparison, chaos, packaging, rolling]:
                path.write_text(json.dumps({"summary": {"error_count": 0}}), encoding="utf-8")

            result = self.run_command(
                sys.executable,
                "tools/attach-release-readiness-evidence.py",
                "--readiness-report",
                str(readiness),
                "--benchmark-report",
                str(benchmark),
                "--load-report",
                str(load),
                "--load-comparison-report",
                str(comparison),
                "--chaos-report",
                str(chaos),
                "--packaging-report",
                str(packaging),
                "--rolling-upgrade-report",
                str(rolling),
                "--release-readiness-file",
                str(release_readiness),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            readiness_payload = json.loads(readiness.read_text(encoding="utf-8"))
            self.assertTrue(readiness_payload["categories"]["release"]["ready"])
            self.assertTrue(readiness_payload["ready"])
            self.assertEqual(readiness_payload["blockers"], [])
            release_payload = json.loads(release_readiness.read_text(encoding="utf-8"))
            self.assertEqual(
                sorted(release_payload),
                [
                    "benchmark_coverage",
                    "chaos_test_coverage",
                    "load_test_coverage",
                    "packaging_verified",
                    "rolling_upgrade_coverage",
                ],
            )
            for item in release_payload.values():
                self.assertTrue(item["passed"])
                self.assertTrue(item["artifact_path"])
                self.assertEqual(item["blockers"], [])

            check = self.run_command(
                sys.executable,
                "tools/check-release-readiness-evidence.py",
                str(release_readiness),
                "--require-passed",
            )

            self.assertEqual(check.returncode, 0, check.stderr)
            check_payload = json.loads(check.stdout)
            self.assertEqual(check_payload["status"], "ok")
            self.assertEqual(check_payload["summary"]["ready_items"], 5)

    def test_attach_release_readiness_evidence_writes_manifest_relative_artifact_paths(self):
        with tempfile.TemporaryDirectory(dir=ROOT) as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            artifacts_dir = temp_dir / "artifacts"
            manifest_dir = temp_dir / "manifest"
            artifacts_dir.mkdir()
            manifest_dir.mkdir()
            readiness = temp_dir / "readiness.json"
            benchmark = artifacts_dir / "benchmark.jsonl"
            load = artifacts_dir / "load.json"
            comparison = artifacts_dir / "comparison.json"
            chaos = artifacts_dir / "chaos.json"
            packaging = artifacts_dir / "packaging.json"
            rolling = artifacts_dir / "rolling.json"
            release_readiness = manifest_dir / "release-readiness.json"

            readiness.write_text(
                json.dumps(
                    {
                        "ready": True,
                        "categories": {
                            "security": {"ready": True, "blockers": []},
                        },
                    }
                ),
                encoding="utf-8",
            )
            benchmark.write_text(json.dumps({"benchmark": "lexical"}) + "\n", encoding="utf-8")
            for path in [load, comparison, chaos, packaging, rolling]:
                path.write_text(json.dumps({"summary": {"error_count": 0}}), encoding="utf-8")

            result = self.run_command(
                sys.executable,
                "tools/attach-release-readiness-evidence.py",
                "--readiness-report",
                str(readiness.relative_to(ROOT)),
                "--benchmark-report",
                str(benchmark.relative_to(ROOT)),
                "--load-report",
                str(load.relative_to(ROOT)),
                "--load-comparison-report",
                str(comparison.relative_to(ROOT)),
                "--chaos-report",
                str(chaos.relative_to(ROOT)),
                "--packaging-report",
                str(packaging.relative_to(ROOT)),
                "--rolling-upgrade-report",
                str(rolling.relative_to(ROOT)),
                "--release-readiness-file",
                str(release_readiness.relative_to(ROOT)),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            readiness_payload = json.loads(readiness.read_text(encoding="utf-8"))
            for item in readiness_payload["release_evidence"].values():
                self.assertTrue(Path(item["path"]).is_absolute())
            release_payload = json.loads(release_readiness.read_text(encoding="utf-8"))
            for item in release_payload.values():
                self.assertTrue(item["artifact_path"].startswith("../artifacts/"))

            check = self.run_command(
                sys.executable,
                "tools/check-release-readiness-evidence.py",
                str(release_readiness),
                "--require-passed",
            )

            self.assertEqual(check.returncode, 0, check.stderr)

    def test_release_readiness_evidence_checker_rejects_missing_artifact(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            manifest = temp_dir / "release-readiness.json"
            for artifact in [
                "benchmark.jsonl",
                "load.json",
                "chaos.json",
                "packaging.json",
                "rolling.json",
            ]:
                if artifact != "chaos.json":
                    (temp_dir / artifact).write_text("{}\n", encoding="utf-8")
            manifest.write_text(
                json.dumps(
                    {
                        "benchmark_coverage": {
                            "passed": True,
                            "artifact_path": "benchmark.jsonl",
                            "blockers": [],
                        },
                        "load_test_coverage": {
                            "passed": True,
                            "artifact_path": "load.json",
                            "blockers": [],
                        },
                        "chaos_test_coverage": {
                            "passed": True,
                            "artifact_path": "chaos.json",
                            "blockers": [],
                        },
                        "packaging_verified": {
                            "passed": True,
                            "artifact_path": "packaging.json",
                            "blockers": [],
                        },
                        "rolling_upgrade_coverage": {
                            "passed": True,
                            "artifact_path": "rolling.json",
                            "blockers": [],
                        },
                    }
                ),
                encoding="utf-8",
            )

            result = self.run_command(
                sys.executable,
                "tools/check-release-readiness-evidence.py",
                str(manifest),
                "--require-passed",
            )

            self.assertEqual(result.returncode, 1)
            payload = json.loads(result.stdout)
            self.assertEqual(payload["status"], "failed")
            self.assertTrue(
                any("chaos_test_coverage.artifact_path" in error for error in payload["errors"])
            )


if __name__ == "__main__":
    unittest.main()
