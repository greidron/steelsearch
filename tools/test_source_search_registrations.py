import csv
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_SEARCH_REGISTRATIONS = (
    ROOT / "docs" / "rust-port" / "generated" / "source-search-registrations.tsv"
)


class SourceSearchRegistrationsTests(unittest.TestCase):
    def _rows(self):
        with SOURCE_SEARCH_REGISTRATIONS.open(newline="", encoding="utf-8") as source_file:
            return list(csv.DictReader(source_file, delimiter="\t"))

    def _status_for_expression_containing(self, category, needle):
        matches = [
            row
            for row in self._rows()
            if row["category"] == category and needle in row["expression"]
        ]
        self.assertEqual(len(matches), 1, needle)
        return matches[0]["status"]

    def test_runtime_backed_search_registrations_are_promoted(self):
        promoted = [
            ("query", "QuerySpec<>(MatchQueryBuilder.NAME,"),
            ("query", "BoolQueryBuilder.NAME"),
            ("query", "ScriptScoreQueryBuilder.NAME"),
            ("aggregation", "AggregationSpec(TermsAggregationBuilder.NAME,"),
            ("aggregation", "AggregationSpec( DateHistogramAggregationBuilder.NAME,"),
            ("aggregation", "TopHitsAggregationBuilder.NAME"),
            ("pipeline_aggregation", "BucketSortPipelineAggregationBuilder.NAME"),
            ("fetch_subphase", "FetchDocValuesPhase"),
            ("fetch_subphase", "ScriptFieldsPhase"),
            ("fetch_subphase", "FetchFieldsPhase"),
            ("fetch_subphase", "FetchVersionPhase"),
            ("fetch_subphase", "HighlightPhase"),
            ("fetch_subphase", "SeqNoPrimaryTermPhase"),
        ]
        for category, needle in promoted:
            self.assertEqual(
                self._status_for_expression_containing(category, needle),
                "implemented",
                f"{category} {needle}",
            )

    def test_unbacked_search_registrations_remain_planned(self):
        planned = [
            ("query", "GeoShapeQueryBuilder.NAME"),
            ("aggregation", "RareTermsAggregationBuilder.NAME"),
            ("aggregation", "GlobalAggregationBuilder.NAME"),
            ("suggester", "TermSuggestionBuilder.SUGGESTION_NAME"),
        ]
        for category, needle in planned:
            self.assertEqual(
                self._status_for_expression_containing(category, needle),
                "planned",
                f"{category} {needle}",
            )


if __name__ == "__main__":
    unittest.main()
