import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-search-extension-point-contracts.py"
CURRENT_SOURCE_SEARCH_REGISTRATIONS = (
    ROOT / "docs/rust-port/generated/source-search-registrations.tsv"
)
CURRENT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"


def load_checker_module():
    module_name = "check_search_extension_point_contracts"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SearchExtensionPointContractsTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_current_generic_search_hook_partials_have_runtime_contracts(self):
        result = self.checker.check_contracts(
            CURRENT_SOURCE_SEARCH_REGISTRATIONS, CURRENT_RUNTIME_SOURCE
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["summary"]["generic_hook_count"], 7)
        self.assertEqual(result["summary"]["partial_generic_row_count"], 7)
        self.assertGreaterEqual(result["summary"]["runtime_contract_count"], 6)
        self.assertEqual(result["summary"]["missing_contract_count"], 0)
        self.assertEqual(result["summary"]["unexpected_partial_row_count"], 0)

    def test_missing_runtime_contract_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source-search-registrations.tsv"
            runtime = temp_dir / "standalone_runtime.rs"
            source.write_text(
                "status\tcategory\texpression\tsource\tline\n"
                "partial\tquery\tQuerySpec<?> spec\tSearchModule.java\t1255\n",
                encoding="utf-8",
            )
            runtime.write_text(
                'SearchExtensionPointContract { steelsearch_point: "aggregation", '
                'opensearch_hook: "registerAggregation(AggregationSpec, ValuesSourceRegistry.Builder)", '
                'status: "rust-native-boundary", evidence: "registry-visible" }',
                encoding="utf-8",
            )

            result = self.checker.check_contracts(source, runtime)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["missing_contract_count"], 1)
            self.assertTrue(
                any("registerQuery(QuerySpec)" in error for error in result["errors"])
            )

    def test_unexpected_partial_row_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source-search-registrations.tsv"
            runtime = temp_dir / "standalone_runtime.rs"
            source.write_text(
                "status\tcategory\texpression\tsource\tline\n"
                "partial\tquery\tnew QuerySpec<>(Unsupported.NAME)\tSearchModule.java\t1\n",
                encoding="utf-8",
            )
            runtime.write_text("", encoding="utf-8")

            result = self.checker.check_contracts(source, runtime)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["unexpected_partial_row_count"], 1)


if __name__ == "__main__":
    unittest.main()
