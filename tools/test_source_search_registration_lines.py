import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CHECKER_PATH = ROOT / "tools" / "check-source-search-registration-lines.py"


def load_checker_module():
    module_name = "check_source_search_registration_lines"
    spec = importlib.util.spec_from_file_location(module_name, CHECKER_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


class SourceSearchRegistrationLinesTests(unittest.TestCase):
    def setUp(self):
        self.checker = load_checker_module()

    def test_accepts_multiline_registration_expression(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "SearchModule.java"
            source.write_text(
                "\n".join(
                    [
                        "registerAggregation(",
                        "    new AggregationSpec(",
                        "        PercentilesAggregationBuilder.NAME,",
                        "        PercentilesAggregationBuilder::new,",
                        "        PercentilesAggregationBuilder::parse",
                        "    ).addResultReader(InternalTDigestPercentiles.NAME, InternalTDigestPercentiles::new)",
                        "     .addResultReader(InternalHDRPercentiles.NAME, InternalHDRPercentiles::new)",
                        "     .setAggregatorRegistrar(PercentilesAggregationBuilder::registerAggregators),",
                        "    builder",
                        ");",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            expression = (
                "new AggregationSpec( PercentilesAggregationBuilder.NAME, "
                "PercentilesAggregationBuilder::new, PercentilesAggregationBuilder::parse )"
                ".addResultReader(InternalTDigestPercentiles.NAME, InternalTDigestPercentiles::new) "
                ".addResultReader(InternalHDRPercentiles.NAME, InternalHDRPercentiles::new) "
                ".setAggregatorRegistrar(PercentilesAggregationBuilder::registerAggregators), builder"
            )
            tsv = temp_dir / "source-search-registrations.tsv"
            tsv.write_text(
                "status\tcategory\texpression\tsource\tline\n"
                f"implemented\taggregation\t{expression}\t{source}\t1\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["errors"], [])
            self.assertEqual(result["summary"]["checked_rows"], 1)

    def test_rejects_row_whose_expression_is_not_in_source_window(self):
        with tempfile.TemporaryDirectory() as temp_dir_value:
            temp_dir = Path(temp_dir_value)
            source = temp_dir / "SearchModule.java"
            source.write_text(
                "new QuerySpec<>(MatchQueryBuilder.NAME, MatchQueryBuilder::new, MatchQueryBuilder::fromXContent);\n",
                encoding="utf-8",
            )
            tsv = temp_dir / "source-search-registrations.tsv"
            tsv.write_text(
                "status\tcategory\texpression\tsource\tline\n"
                f"implemented\tquery\tnew QuerySpec<>(MissingQueryBuilder.NAME, MissingQueryBuilder::new, MissingQueryBuilder::fromXContent)\t{source}\t1\n",
                encoding="utf-8",
            )

            result = self.checker.validate_source(tsv)

            self.assertEqual(result["status"], "failed")
            self.assertIn("MissingQueryBuilder", json.dumps(result["errors"]))


if __name__ == "__main__":
    unittest.main()
