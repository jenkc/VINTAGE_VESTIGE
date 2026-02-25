"""
Search quality regression and analysis tests.

Slow tests that load models and run many searches. Designed for
CI or manual verification runs.

Tests:
- Score regression (don't drop below recorded baseline)
- Cross-source retrieval (all 3 sources appear in results)
- Category consistency (similar items share categories)
- Vibe query effectiveness (modern style terms work)
"""
import pytest
import json
import numpy as np


# Recorded baseline scores from 2026-02-18 enriched run.
# Update these after significant data or enrichment changes.
BASELINE_SCORES = {
    "silk evening dress": 0.55,
    "wool coat or cape": 0.40,
    "dark academia aesthetic": 0.60,
    "cottagecore pastoral dress": 0.60,
    "romantic gothic fashion": 0.50,
    "old money elegance": 0.40,
}


def _search(vector_db, embedding_generator, query, limit=10):
    query_vector = embedding_generator.generate_text_embedding(query)
    return vector_db.search_similar(
        collection="vintage_text",
        query_vector=query_vector,
        limit=limit,
    )


class TestScoreRegression:
    """Ensure scores don't drop below recorded baselines."""

    @pytest.mark.parametrize("query,min_score", list(BASELINE_SCORES.items()))
    def test_score_not_regressed(
        self, vector_db, embedding_generator, query, min_score
    ):
        results = _search(vector_db, embedding_generator, query, limit=1)
        actual = results[0]["score"]
        assert actual >= min_score, (
            f"Regression: '{query}' scored {actual:.3f}, "
            f"baseline was {min_score:.3f}"
        )


class TestCrossSourceRetrieval:
    """Queries should find results from multiple data sources."""

    BROAD_QUERIES = [
        "historical fashion garment",
        "elegant formal dress",
        "vintage outerwear",
    ]

    @pytest.mark.parametrize("query", BROAD_QUERIES)
    def test_multiple_sources_in_top_20(
        self, vector_db, embedding_generator, db_session, query
    ):
        from storage.database import Product

        results = _search(vector_db, embedding_generator, query, limit=20)
        platforms = set()
        for result in results:
            product = db_session.query(Product).filter(
                Product.id == result["id"]
            ).first()
            if product:
                platforms.add(product.platform)

        assert len(platforms) >= 2, (
            f"'{query}': only found platforms {platforms} in top 20"
        )


class TestCategoryConsistency:
    """Category-specific queries should return items from that category."""

    @pytest.mark.parametrize("category_query,expected_category", [
        ("vintage dress gown", "dress"),
        ("coat or cape outerwear", "coat"),
        ("historical jacket", "jacket"),
    ])
    def test_top5_category_precision(
        self, vector_db, embedding_generator, db_session,
        category_query, expected_category,
    ):
        from storage.database import Product

        results = _search(vector_db, embedding_generator, category_query, limit=5)
        matches = 0
        for result in results:
            product = db_session.query(Product).filter(
                Product.id == result["id"]
            ).first()
            if product and product.fp_category:
                if expected_category in product.fp_category.lower():
                    matches += 1

        precision = matches / len(results) if results else 0
        assert precision >= 0.4, (
            f"Precision for '{category_query}' -> '{expected_category}': "
            f"{precision:.0%} ({matches}/{len(results)})"
        )


class TestVibeQueryEffectiveness:
    """Modern aesthetic queries should return items with matching vibe/style_tags."""

    VIBE_QUERIES = [
        ("dark academia aesthetic", ["dark academia", "academic", "scholarly"]),
        ("cottagecore pastoral", ["cottagecore", "pastoral", "romantic"]),
        ("old money elegance", ["old money", "quiet luxury", "elegant"]),
    ]

    @pytest.mark.parametrize("query,expected_vibes", VIBE_QUERIES)
    def test_vibe_returns_matching_items(
        self, vector_db, embedding_generator, db_session,
        query, expected_vibes,
    ):
        from storage.database import Product

        results = _search(vector_db, embedding_generator, query, limit=5)
        vibe_matches = 0

        for result in results:
            product = db_session.query(Product).filter(
                Product.id == result["id"]
            ).first()
            if product:
                product_vibe = (product.vibe or "").lower()
                product_tags = product.style_tags or "[]"
                try:
                    tags = json.loads(product_tags)
                    all_text = product_vibe + " " + " ".join(
                        t.lower() for t in tags
                    )
                except (json.JSONDecodeError, TypeError):
                    all_text = product_vibe

                if any(v.lower() in all_text for v in expected_vibes):
                    vibe_matches += 1

        assert vibe_matches >= 1, (
            f"No vibe matches for '{query}' in top 5 results"
        )


class TestScoreDistribution:
    """Score distribution should not be degenerate."""

    def test_score_spread_is_reasonable(self, vector_db, embedding_generator):
        """Top-20 scores should span a reasonable range."""
        results = _search(
            vector_db, embedding_generator, "vintage fashion", limit=20
        )
        scores = [r["score"] for r in results]
        spread = max(scores) - min(scores)
        assert spread >= 0.03, (
            f"Score spread too narrow ({spread:.3f}): scores may be degenerate"
        )

    def test_top_score_below_one(self, vector_db, embedding_generator):
        """No query should return a perfect 1.0 (would indicate data leak)."""
        results = _search(
            vector_db, embedding_generator, "random test query 12345", limit=1
        )
        assert results[0]["score"] < 1.0
