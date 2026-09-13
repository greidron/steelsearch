import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import core_search_fixture as scope


class CoreSearchFixtureTests(unittest.TestCase):
    def test_removes_only_plugin_cases_and_setup(self):
        source = json.loads(scope.SOURCE.read_text())
        saved = copy.deepcopy(source)
        projected = scope.project(source)
        self.assertEqual(source, saved)
        self.assertEqual(len(projected["cases"]), 1180)
        self.assertEqual(len(projected["indices"]), len(source["indices"]) - 3)
        self.assertEqual(len(projected["bulk"]), len(source["bulk"]) - 3)
        self.assertEqual(len(projected["aliases"]), len(source["aliases"]) - 3)
        self.assertFalse(scope.contains_removed_reference(projected))
        for key in source.keys() - {"cases", "indices", "bulk", "aliases", "manifest"}:
            self.assertEqual(projected[key], source[key])

    def test_core_exclusion_and_retained_reference_fail(self):
        source = json.loads(scope.SOURCE.read_text())
        core = next(case for case in source["cases"] if case.get("area") == "search")
        with patch.object(scope, "excluded_names", return_value={core["name"]}), self.assertRaises(ValueError):
            scope.project(source)
        core["path"] = "/vectors-compat/_search"
        with self.assertRaisesRegex(ValueError, "references removed"):
            scope.project(source)

    def test_rehashed_projection_cannot_drop_core_case(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "fixture.json"
            metadata = scope.write_projection(path)
            suite = {"fixture_path": str(path), "core_search_fixture_projection": metadata}
            self.assertEqual(scope.validate_projection(suite), [])
            fixture = json.loads(path.read_text())
            fixture["cases"].pop()
            raw = json.dumps(fixture).encode()
            path.write_bytes(raw)
            metadata["projected_sha256"] = hashlib.sha256(raw).hexdigest()
            self.assertTrue(scope.validate_projection(suite))


if __name__ == "__main__":
    unittest.main()
