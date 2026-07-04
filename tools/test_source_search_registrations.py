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
            ("query", "GeoBoundingBoxQueryBuilder.NAME"),
            ("query", "GeoPolygonQueryBuilder.NAME"),
            ("query", "GeoShapeQueryBuilder.NAME"),
            ("query", "SpanGapQueryBuilder.NAME"),
            ("query", "ScriptQueryBuilder.NAME"),
            ("query", "ScriptScoreQueryBuilder.NAME"),
            ("query", "IntervalQueryBuilder.NAME"),
            ("query", "TemplateQueryBuilder.NAME"),
            ("aggregation", "AggregationSpec(TermsAggregationBuilder.NAME,"),
            ("aggregation", "AdjacencyMatrixAggregationBuilder.NAME"),
            ("aggregation", "AggregationSpec( DateHistogramAggregationBuilder.NAME,"),
            ("aggregation", "DateRangeAggregationBuilder.NAME"),
            ("aggregation", "DiversifiedAggregationBuilder.NAME"),
            ("aggregation", "GeoDistanceAggregationBuilder.NAME"),
            ("aggregation", "IpRangeAggregationBuilder.NAME"),
            ("aggregation", "MultiTermsAggregationBuilder.NAME"),
            ("aggregation", "AggregationSpec(NestedAggregationBuilder.NAME"),
            ("aggregation", "RareTermsAggregationBuilder.NAME"),
            ("aggregation", "SamplerAggregationBuilder.NAME"),
            ("aggregation", "GlobalAggregationBuilder.NAME"),
            ("aggregation", "ReverseNestedAggregationBuilder.NAME"),
            ("aggregation", "SignificantTextAggregationBuilder.NAME"),
            ("aggregation", "TopHitsAggregationBuilder.NAME"),
            ("aggregation", "VariableWidthHistogramAggregationBuilder.NAME"),
            ("pipeline_aggregation", "BucketSortPipelineAggregationBuilder.NAME"),
            ("suggester", "TermSuggestionBuilder.SUGGESTION_NAME"),
            ("suggester", "PhraseSuggestionBuilder.SUGGESTION_NAME"),
            ("suggester", "CompletionSuggestionBuilder.SUGGESTION_NAME"),
            ("score_function", "ScriptScoreFunctionBuilder.NAME"),
            ("score_function", "GaussDecayFunctionBuilder.NAME"),
            ("score_function", "LinearDecayFunctionBuilder.NAME"),
            ("score_function", "ExponentialDecayFunctionBuilder.NAME"),
            ("score_function", "RandomScoreFunctionBuilder.NAME"),
            ("score_function", "FieldValueFactorFunctionBuilder.NAME"),
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

    def test_generic_search_extension_hooks_are_implemented(self):
        implemented = [
            ("aggregation", "agg, builder"),
            ("aggregation", "AggregationSpec spec, ValuesSourceRegistry.Builder builder"),
            ("pipeline_aggregation", "PipelineAggregationSpec spec"),
            ("suggester", "SuggesterSpec<?> suggester"),
            ("score_function", "ScoreFunctionSpec<?> scoreFunction"),
            ("fetch_subphase", "FetchSubPhase subPhase"),
            ("query", "QuerySpec<?> spec"),
        ]
        for category, needle in implemented:
            self.assertEqual(
                self._status_for_expression_containing(category, needle),
                "implemented",
                f"{category} {needle}",
            )


if __name__ == "__main__":
    unittest.main()
