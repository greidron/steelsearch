import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_REST_ROUTES = ROOT / "docs" / "rust-port" / "generated" / "source-rest-routes.tsv"


class SourceRestRoutesTests(unittest.TestCase):
    def test_head_index_route_is_promoted_with_runtime_handler_evidence(self):
        with SOURCE_REST_ROUTES.open(newline="", encoding="utf-8") as routes_file:
            rows = list(csv.DictReader(routes_file, delimiter="\t"))

        route = next(
            row
            for row in rows
            if row["method"] == "HEAD" and row["path_or_expression"] == "/{index}"
        )
        self.assertEqual(route["status"], "implemented")
        self.assertTrue(route["source"].endswith("RestGetIndicesAction.java"))

    def test_runtime_backed_source_routes_stay_promoted(self):
        with SOURCE_REST_ROUTES.open(newline="", encoding="utf-8") as routes_file:
            rows = list(csv.DictReader(routes_file, delimiter="\t"))

        statuses = {
            (row["method"], row["path_or_expression"]): row["status"] for row in rows
        }
        promoted_routes = [
            ("GET", "/ + ENDPOINT"),
            ("POST", "/_reindex"),
            ("POST", "/_reindex/{taskId}/_rethrottle"),
            ("POST", "/_filecache/prune"),
            ("GET", "_wlm/stats"),
            ("PUT", "/{index}/_block/{block}"),
            ("POST", "/{index}/_rollover"),
            ("GET", "/_flush/synced"),
            ("POST", "/_upgrade"),
            ("GET", "/_cat/snapshots/{repository}"),
        ]
        for method, path in promoted_routes:
            self.assertEqual(statuses[(method, path)], "implemented", f"{method} {path}")


if __name__ == "__main__":
    unittest.main()
