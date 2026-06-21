import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGING_PATH = ROOT / "tools" / "generate-packaging-evidence.py"


def load_packaging_module():
    module_name = "generate_packaging_evidence"
    spec = importlib.util.spec_from_file_location(module_name, PACKAGING_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class PackagingEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.packaging = load_packaging_module()

    def test_generate_report_accepts_minimal_release_package_surface(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            write_package_fixture(root)

            report = self.packaging.generate_report(root, skip_build=True)

            self.assertTrue(report["ready"])
            self.assertTrue(report["passed"])
            self.assertTrue(report["summary"]["passed"])
            self.assertEqual(report["summary"]["error_count"], 0)
            self.assertTrue(report["summary"]["binary_present"])
            self.assertTrue(report["summary"]["binary_executable"])
            self.assertEqual(report["cargo_package"]["package_version"], "0.2.2")

    def test_generate_report_rejects_dockerfile_without_required_feature(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            write_package_fixture(root)
            dockerfile = root / "Dockerfile"
            dockerfile.write_text(
                dockerfile.read_text(encoding="utf-8").replace(
                    "--features standalone-runtime ",
                    "",
                ),
                encoding="utf-8",
            )

            report = self.packaging.generate_report(root, skip_build=True)

            self.assertFalse(report["ready"])
            self.assertIn(
                "Dockerfile is missing snippet: --features standalone-runtime",
                report["blockers"],
            )

    def test_cli_writes_packaging_report(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            root = Path(temp_dir_value)
            output = root / "target/release-packaging/packaging-report.json"
            write_package_fixture(root)

            result = subprocess.run(
                [
                    sys.executable,
                    str(PACKAGING_PATH),
                    "--root",
                    str(root),
                    "--output",
                    str(output),
                    "--skip-build",
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(output.is_file())
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(payload["summary"]["passed"])
            self.assertEqual(payload["summary"]["error_count"], 0)


def write_package_fixture(root: Path):
    cargo_dir = root / "crates/os-node"
    cargo_dir.mkdir(parents=True)
    cargo_dir.joinpath("Cargo.toml").write_text(
        """
[package]
name = "os-node"
version = "0.2.2"

[features]
standalone-runtime = []

[[bin]]
name = "steelsearch"
path = "src/main.rs"
required-features = ["standalone-runtime"]
""".strip()
        + "\n",
        encoding="utf-8",
    )
    root.joinpath("Dockerfile").write_text(
        """
FROM rust:1.76-bookworm AS builder
RUN cargo build --release -p os-node --features standalone-runtime --bin steelsearch
COPY --from=builder /workspace/target/release/steelsearch /usr/local/bin/steelsearch
USER steelsearch
EXPOSE 9200 9300
""".strip()
        + "\n",
        encoding="utf-8",
    )
    binary = root / "target/release/steelsearch"
    binary.parent.mkdir(parents=True)
    binary.write_text("#!/bin/sh\n", encoding="utf-8")
    binary.chmod(binary.stat().st_mode | stat.S_IXUSR)


if __name__ == "__main__":
    unittest.main()
