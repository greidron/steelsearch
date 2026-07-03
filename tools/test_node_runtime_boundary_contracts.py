import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-node-runtime-boundary-contracts.py"
CURRENT_SOURCE_NODE_RUNTIME = (
    ROOT / "docs/rust-port/generated/source-node-runtime-components.tsv"
)
CURRENT_RUNTIME_SOURCE = ROOT / "crates/os-node/src/standalone_runtime.rs"


def load_checker_module():
    module_name = "check_node_runtime_boundary_contracts"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class NodeRuntimeBoundaryContractsTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_current_node_runtime_partials_have_boundary_owner_mappings(self):
        result = self.checker.check_contracts(
            CURRENT_SOURCE_NODE_RUNTIME, CURRENT_RUNTIME_SOURCE
        )

        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["errors"], [])
        self.assertEqual(result["summary"]["source_node_runtime_count"], 78)
        self.assertEqual(result["summary"]["partial_component_count"], 78)
        self.assertEqual(result["summary"]["owner_mapping_count"], 78)
        self.assertGreater(result["summary"]["code_visible_boundary_count"], 0)
        self.assertEqual(result["summary"]["missing_owner_count"], 0)
        self.assertEqual(result["summary"]["stale_owner_count"], 0)

    def test_missing_owner_mapping_fails(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source-node-runtime-components.tsv"
            runtime = temp_dir / "standalone_runtime.rs"
            source.write_text(
                "status\tkind\tcomponent\tsource\tline\n"
                "partial\tservice\tSyntheticService\tNode.java\t1\n",
                encoding="utf-8",
            )
            runtime.write_text("", encoding="utf-8")

            result = self.checker.check_contracts(source, runtime)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["summary"]["missing_owner_count"], 1)
            self.assertTrue(any("SyntheticService" in error for error in result["errors"]))

    def test_code_visible_boundary_must_be_in_source_inventory(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "source-node-runtime-components.tsv"
            runtime = temp_dir / "standalone_runtime.rs"
            source.write_text(
                "status\tkind\tcomponent\tsource\tline\n"
                "partial\tservice\tPluginsService\tNode.java\t1\n",
                encoding="utf-8",
            )
            runtime.write_text(
                'RuntimeComponentBoundary { opensearch_component: "NotInSourceService", '
                'steelsearch_owner: "owner", status: "partial", evidence: &[] }',
                encoding="utf-8",
            )

            result = self.checker.check_contracts(source, runtime)

            self.assertEqual(result["status"], "failed")
            self.assertEqual(
                result["summary"]["code_visible_missing_from_source_count"], 1
            )
            self.assertTrue(
                any("NotInSourceService" in error for error in result["errors"])
            )


if __name__ == "__main__":
    unittest.main()
