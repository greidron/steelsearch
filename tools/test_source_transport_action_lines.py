import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-transport-action-lines.py"


def load_checker_module():
    module_name = "check_source_transport_action_lines"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceTransportActionLinesTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_single_line_and_multiline_source_registrations(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "ActionModule.java"
            source.write_text(
                "\n".join(
                    [
                        "actions.register(MainAction.INSTANCE, TransportMainAction.class);",
                        "actions.register(",
                        "    MultiTermVectorsAction.INSTANCE,",
                        "    TransportMultiTermVectorsAction.class,",
                        "    TransportShardMultiTermsVectorAction.class",
                        ");",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            tsv = temp_dir / "source-transport-actions.tsv"
            tsv.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                f"implemented\tMainAction.INSTANCE\tTransportMainAction.class\t{source}\t1\n"
                f"implemented\tMultiTermVectorsAction.INSTANCE\tTransportMultiTermVectorsAction.class\t{source}\t2\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["summary"]["checked_rows"], 2)

    def test_rejects_rows_whose_source_window_lacks_handler(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "ActionModule.java"
            source.write_text(
                "actions.register(SearchAction.INSTANCE, TransportSearchAction.class);\n",
                encoding="utf-8",
            )
            tsv = temp_dir / "source-transport-actions.tsv"
            tsv.write_text(
                "status\taction\ttransport_handler\tsource\tline\n"
                f"implemented\tSearchAction.INSTANCE\tMissingTransportAction.class\t{source}\t1\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "failed")
            self.assertIn("MissingTransportAction.class", json.dumps(result["errors"]))


if __name__ == "__main__":
    unittest.main()
