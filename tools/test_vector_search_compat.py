import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("vector_search_compat.py")
sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("vector_search_compat", MODULE_PATH)
vector_search_compat = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(vector_search_compat)


class VectorSearchCompatTests(unittest.TestCase):
    def test_error_summary_includes_first_root_cause(self):
        response = {
            "status": 400,
            "body": {
                "error": {
                    "type": "x_content_parse_exception",
                    "reason": "[1:69] [knn] unknown field [bogus_parameter]",
                    "root_cause": [
                        {
                            "type": "x_content_parse_exception",
                            "reason": "[1:69] [knn] unknown field [bogus_parameter]",
                        }
                    ],
                },
                "status": 400,
            },
        }

        self.assertEqual(
            vector_search_compat.error_summary(response),
            {
                "status": 400,
                "error_type": "x_content_parse_exception",
                "error_reason": "[1:69] [knn] unknown field [bogus_parameter]",
                "root_cause_type": "x_content_parse_exception",
                "root_cause_reason": "[1:69] [knn] unknown field [bogus_parameter]",
            },
        )


if __name__ == "__main__":
    unittest.main()
