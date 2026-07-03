import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-node-runtime-lines.py"


def load_checker_module():
    module_name = "check_source_node_runtime_lines"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceNodeRuntimeLinesTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_component_in_source_window(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "Node.java"
            source.write_text(
                "final ClusterService clusterService = new ClusterService(settings);\n"
                "final TransportService transportService = new TransportService(settings);\n",
                encoding="utf-8",
            )
            tsv = temp_dir / "source-node-runtime-components.tsv"
            tsv.write_text(
                "status\tkind\tcomponent\tsource\tline\n"
                f"partial\tservice\tClusterService\t{source}\t1\n"
                f"partial\tservice\tTransportService\t{source}\t2\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["summary"]["checked_rows"], 2)

    def test_rejects_row_whose_component_is_not_in_source_window(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "Node.java"
            source.write_text("final SearchService searchService = null;\n", encoding="utf-8")
            tsv = temp_dir / "source-node-runtime-components.tsv"
            tsv.write_text(
                "status\tkind\tcomponent\tsource\tline\n"
                f"partial\tservice\tTransportService\t{source}\t1\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "failed")
            self.assertIn("TransportService", json.dumps(result["errors"]))


if __name__ == "__main__":
    unittest.main()
