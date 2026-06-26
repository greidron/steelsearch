import json
import sys
import unittest
from pathlib import Path


TOOLS_DIR = Path(__file__).resolve().parent
ROOT = TOOLS_DIR.parent
sys.path.insert(0, str(TOOLS_DIR))

import migration_cutover_integration


class MigrationCutoverCapabilityTests(unittest.TestCase):
    def test_source_capabilities_detect_missing_knn_plugin_from_create_index_error(self):
        response = {
            "status": 400,
            "body": {
                "error": {
                    "type": "settings_exception",
                    "reason": (
                        "unknown setting [index.knn] please check that any required "
                        "plugins are installed"
                    ),
                }
            },
        }

        self.assertTrue(migration_cutover_integration.missing_knn_plugin_response(response))
        summary = migration_cutover_integration.source_capability_summary(
            [{"name": "create_vector_index", **response}]
        )

        self.assertEqual(summary["missing"], ["knn"])
        self.assertEqual(summary["evidence"][0]["capability"], "knn")
        self.assertEqual(summary["evidence"][0]["status"], 400)

    def test_vector_ranking_check_is_gated_by_source_knn_capability(self):
        fixture = json.loads(
            (ROOT / "tools" / "fixtures" / "migration-cutover-integration.json").read_text(
                encoding="utf-8"
            )
        )
        checks = {check["name"]: check for check in fixture["checks"]}

        self.assertEqual(checks["vector_knn_ranking"]["source_capabilities"], ["knn"])
        self.assertEqual(
            migration_cutover_integration.missing_required_source_capabilities(
                checks["vector_knn_ranking"],
                {"missing": ["knn"]},
            ),
            ["knn"],
        )

    def test_migration_promotion_gate_no_longer_claims_vector_ranking_profile(self):
        fixture = json.loads(
            (ROOT / "tools" / "fixtures" / "migration-promotion-gate.json").read_text(
                encoding="utf-8"
            )
        )
        semantic = fixture["unified_report_sections"]["semantic_parity"]

        self.assertNotIn("vector_knn_ranking", semantic["required_cases"])
        self.assertNotIn("vector-ranking-equivalence", semantic["required_evidence_classes"])


if __name__ == "__main__":
    unittest.main()
