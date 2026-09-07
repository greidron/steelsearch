import hashlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_benchmark_telemetry_scripts import load_matrix_module


class BenchmarkBinarySelectionTests(unittest.TestCase):
    def setUp(self):
        self.matrix = load_matrix_module()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.binary = self.root / "previous-release"
        self.binary.write_bytes(b"previous release executable")
        self.binary.chmod(0o755)

    def test_absolute_override_is_used_instead_of_current_release(self):
        with patch.dict(os.environ, {"STEELSEARCH_BINARY_PATH": str(self.binary)}):
            self.assertEqual(self.matrix.existing_steelsearch_release_binary(), self.binary)

    def test_relative_override_resolves_against_repository_root(self):
        with patch.object(self.matrix, "ROOT", self.root):
            with patch.dict(os.environ, {"STEELSEARCH_BINARY_PATH": self.binary.name}):
                self.assertEqual(self.matrix.existing_steelsearch_release_binary(), self.binary)

    def test_invalid_override_never_falls_back_to_current_release(self):
        with patch.dict(os.environ, {"STEELSEARCH_BINARY_PATH": str(self.root / "missing")}):
            with self.assertRaisesRegex(RuntimeError, "missing or not executable"):
                self.matrix.existing_steelsearch_release_binary()

    def test_non_executable_override_is_rejected(self):
        self.binary.chmod(0o644)
        with patch.dict(os.environ, {"STEELSEARCH_BINARY_PATH": str(self.binary)}):
            with self.assertRaises(RuntimeError):
                self.matrix.existing_steelsearch_release_binary()

    def test_default_is_used_without_override(self):
        with patch.object(self.matrix, "STEELSEARCH_RELEASE_BINARY", self.binary):
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(self.matrix.existing_steelsearch_release_binary(), self.binary)

    def test_fingerprint_identifies_actual_bytes_and_detects_replacement(self):
        evidence = self.matrix.executable_evidence(self.binary)
        self.assertEqual(evidence["path"], str(self.binary))
        self.assertEqual(evidence["sha256"], hashlib.sha256(self.binary.read_bytes()).hexdigest())
        self.binary.write_bytes(b"different executable")
        self.assertNotEqual(evidence, self.matrix.executable_evidence(self.binary))


if __name__ == "__main__":
    unittest.main()
