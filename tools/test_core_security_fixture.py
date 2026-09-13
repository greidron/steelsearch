import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from core_security_fixture import SOURCE, EXCLUDED, project, write_projection, validate_projection


class CoreSecurityFixtureTests(unittest.TestCase):
    def test_only_reviewed_plugin_cases_removed(self):
        source = json.loads(SOURCE.read_text())
        saved = copy.deepcopy(source)
        projected = project(source)
        self.assertEqual(source, saved)
        self.assertEqual(len(projected["cases"]), 59)
        self.assertEqual({c["name"] for c in source["cases"]} - {c["name"] for c in projected["cases"]}, EXCLUDED)
        self.assertEqual({k:v for k,v in source.items() if k != "cases"},
                         {k:v for k,v in projected.items() if k != "cases"})

    def test_projection_rejects_core_case_or_setup_changes_even_with_new_hash(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.json"
            metadata = write_projection(path)
            suite = {"fixture_path": str(path), "core_fixture_projection": metadata}
            self.assertEqual(validate_projection(suite), [])
            original = path.read_bytes()
            for key in ("cases", "indices", "credential_sets"):
                value = json.loads(original)
                value[key] = [] if key != "credential_sets" else {}
                raw = json.dumps(value).encode()
                path.write_bytes(raw)
                metadata["projected_sha256"] = hashlib.sha256(raw).hexdigest()
                with self.subTest(key=key):
                    self.assertTrue(validate_projection(suite))

    def test_missing_exclusion_drift_and_overwrite_fail(self):
        source = json.loads(SOURCE.read_text())
        source["cases"] = [case for case in source["cases"] if case["name"] not in EXCLUDED]
        with self.assertRaises(ValueError):
            project(source)
        self.assertTrue(validate_projection({}))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.json"
            write_projection(path)
            with self.assertRaises(FileExistsError):
                write_projection(path)


if __name__ == "__main__":
    unittest.main()
