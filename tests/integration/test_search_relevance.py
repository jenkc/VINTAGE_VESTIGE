"""
Integration tests for search relevance.

Same 14 queries from the evaluation scripts, now with real assertions
and minimum score thresholds. Serves as regression tests — if enrichment
or re-embedding degrades quality, these tests fail.
"""
import pytest


# Minimum acceptable top-1 score thresholds (conservative, post-enrichment).
# Calibrated from the 2026-02-18 enriched run (overall avg 0.617).
# Set at ~75-80% of observed values to avoid flaky failures.
BASIC_MIN_SCORE = 0.35
ERA_MIN_SCORE = 0.45
CULTURE_MIN_SCORE = 0.25
VIBE_MIN_SCORE = 0.40


BASIC_QUERIES = [
    ("silk evening dress", "Should find evening dresses"),
    ("wool coat or cape", "Should find outerwear"),
    ("lace bonnet", "Should find bonnets/headwear"),
    ("embroidered waistcoat", "Should find waistcoats"),
]

ERA_QUERIES = [
    ("18th century robe", "Should find 1700s robes/gowns"),
    ("1800s Victorian dress", "Should find 19th century items"),
    ("Georgian era fashion", "Should find 1700s-1800s items"),
]

CULTURE_QUERIES = [
    ("French silk gown", "Should find French items"),
    ("British corset or stays", "Should find British items"),
    ("American formal wear", "Should find American items"),
]

VIBE_QUERIES = [
    ("dark academia aesthetic", "Modern vibe query"),
    ("cottagecore pastoral dress", "Modern vibe query"),
    ("romantic gothic fashion", "Modern vibe query"),
    ("old money elegance", "Modern vibe query"),
]


def _search(vector_db, embedding_generator, query, limit=5):
    """Embed query and search vintage_text collection."""
    query_vector = embedding_generator.generate_text_embedding(query)
    return vector_db.search_similar(
        collection="vintage_text",
        query_vector=query_vector,
        limit=limit,
    )


class TestBasicQueries:

    @pytest.mark.parametrize("query,description", BASIC_QUERIES)
    def test_score_above_threshold(
        self, vector_db, embedding_generator, query, description
    ):
        results = _search(vector_db, embedding_generator, query)
        assert len(results) > 0, f"No results for '{query}'"
        top_score = results[0]["score"]
        assert top_score >= BASIC_MIN_SCORE, (
            f"'{query}': top score {top_score:.3f} < {BASIC_MIN_SCORE}"
        )

    @pytest.mark.parametrize("query,description", BASIC_QUERIES)
    def test_returns_five_results(
        self, vector_db, embedding_generator, query, description
    ):
        results = _search(vector_db, embedding_generator, query, limit=5)
        assert len(results) == 5


class TestEraQueries:

    @pytest.mark.parametrize("query,description", ERA_QUERIES)
    def test_score_above_threshold(
        self, vector_db, embedding_generator, query, description
    ):
        results = _search(vector_db, embedding_generator, query)
        top_score = results[0]["score"]
        assert top_score >= ERA_MIN_SCORE, (
            f"'{query}': top score {top_score:.3f} < {ERA_MIN_SCORE}"
        )


class TestCultureQueries:

    @pytest.mark.parametrize("query,description", CULTURE_QUERIES)
    def test_score_above_threshold(
        self, vector_db, embedding_generator, query, description
    ):
        results = _search(vector_db, embedding_generator, query)
        top_score = results[0]["score"]
        assert top_score >= CULTURE_MIN_SCORE, (
            f"'{query}': top score {top_score:.3f} < {CULTURE_MIN_SCORE}"
        )


class TestVibeQueries:

    @pytest.mark.parametrize("query,description", VIBE_QUERIES)
    def test_score_above_threshold(
        self, vector_db, embedding_generator, query, description
    ):
        results = _search(vector_db, embedding_generator, query)
        top_score = results[0]["score"]
        assert top_score >= VIBE_MIN_SCORE, (
            f"'{query}': top score {top_score:.3f} < {VIBE_MIN_SCORE}"
        )


class TestSearchQualityAggregates:

    def test_overall_average_above_minimum(self, vector_db, embedding_generator):
        """Overall average top-1 score across all 14 queries >= 0.50."""
        all_queries = BASIC_QUERIES + ERA_QUERIES + CULTURE_QUERIES + VIBE_QUERIES
        scores = []
        for query, _ in all_queries:
            results = _search(vector_db, embedding_generator, query)
            scores.append(results[0]["score"])

        avg = sum(scores) / len(scores)
        assert avg >= 0.50, f"Overall average {avg:.3f} below 0.50"

    def test_vibe_average_above_baseline(self, vector_db, embedding_generator):
        """Vibe queries should average >= 0.50 post-enrichment."""
        scores = []
        for query, _ in VIBE_QUERIES:
            results = _search(vector_db, embedding_generator, query)
            scores.append(results[0]["score"])

        avg = sum(scores) / len(scores)
        assert avg >= 0.50, (
            f"Vibe average {avg:.3f} below 0.50 (enrichment regression?)"
        )

    def test_ranking_quality_top3_decreasing(self, vector_db, embedding_generator):
        """For every query, scores in top-3 should be non-increasing."""
        all_queries = BASIC_QUERIES + ERA_QUERIES + CULTURE_QUERIES + VIBE_QUERIES
        for query, _ in all_queries:
            results = _search(vector_db, embedding_generator, query, limit=3)
            scores = [r["score"] for r in results]
            assert scores == sorted(scores, reverse=True), (
                f"'{query}': not in descending order: {scores}"
            )
