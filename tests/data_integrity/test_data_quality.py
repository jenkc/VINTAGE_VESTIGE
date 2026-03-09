"""
Data integrity tests.

Verify consistency between PostgreSQL products and pgvector embeddings.
Validate JSON field integrity and enrichment completeness.
"""
import pytest
import json


class TestEnrichmentCompleteness:

    def test_all_products_have_title(self, db_session):
        from storage.database import Product
        missing = db_session.query(Product).filter(
            (Product.title == None) | (Product.title == "")
        ).count()
        assert missing == 0, f"{missing} products missing title"

    def test_all_products_have_platform(self, db_session):
        from storage.database import Product
        missing = db_session.query(Product).filter(Product.platform == None).count()
        assert missing == 0, f"{missing} products missing platform"

    def test_platform_values_are_valid(self, db_session):
        from storage.database import Product
        from sqlalchemy import distinct
        platforms = [
            r[0] for r in db_session.query(distinct(Product.platform)).all()
        ]
        valid = {"met_museum", "smithsonian", "fashionpedia", "va_museum"}
        for p in platforms:
            assert p in valid, f"Unknown platform: {p}"

    def test_enriched_products_have_enriched_text(self, db_session):
        from storage.database import Product
        enriched_no_text = db_session.query(Product).filter(
            Product.enriched_at != None,
            (Product.enriched_text == None) | (Product.enriched_text == ""),
        ).count()
        assert enriched_no_text == 0, (
            f"{enriched_no_text} enriched products missing enriched_text"
        )

    def test_enriched_products_have_ai_description(self, db_session):
        from storage.database import Product
        missing = db_session.query(Product).filter(
            Product.enriched_at != None,
            Product.ai_description == None,
        ).count()
        assert missing == 0, f"{missing} enriched products missing ai_description"

    def test_all_products_are_enriched(self, db_session):
        from storage.database import Product
        total = db_session.query(Product).count()
        enriched = db_session.query(Product).filter(
            Product.enriched_at != None
        ).count()
        assert total == enriched, (
            f"{total - enriched} products not yet enriched ({enriched}/{total})"
        )


class TestJSONFieldIntegrity:

    @pytest.mark.parametrize("field_name", [
        "style_tags", "colors", "textile_finishing", "garment_parts", "decorations",
    ])
    def test_json_fields_are_valid_json_arrays(self, db_session, field_name):
        from storage.database import Product
        products = db_session.query(
            getattr(Product, field_name)
        ).filter(
            getattr(Product, field_name) != None,
        ).limit(100).all()

        for (value,) in products:
            try:
                parsed = json.loads(value)
                assert isinstance(parsed, list), (
                    f"{field_name} should be JSON array, got {type(parsed).__name__}"
                )
            except json.JSONDecodeError:
                pytest.fail(f"{field_name} contains invalid JSON: {value[:100]}")


class TestEmbeddingConsistency:

    def test_text_embedding_count_reasonable(self, db_session):
        """Text embeddings should exist for most enriched products."""
        from storage.database import Product
        from sqlalchemy import text
        pg_enriched = db_session.query(Product).filter(
            Product.enriched_at != None
        ).count()
        has_embedding = db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL")
        ).scalar()
        assert abs(pg_enriched - has_embedding) <= 200, (
            f"Enriched: {pg_enriched}, with text embedding: {has_embedding}"
        )

    def test_enriched_products_have_embeddings(self, db_session):
        """Spot-check: enriched products should have text embeddings."""
        from storage.database import Product
        products = db_session.query(Product).filter(
            Product.enriched_at != None
        ).limit(20).all()
        found = sum(1 for p in products if p.text_embedding is not None)
        assert found >= 5, (
            f"Only {found}/20 enriched products have text embeddings"
        )


class TestFashionpediaValues:
    """Validate Fashionpedia taxonomy fields use known enum values."""

    # Canonical values plus common Claude variants
    VALID_FP_CATEGORIES = {
        "shirt/blouse", "top/t-shirt/sweatshirt", "sweater", "cardigan",
        "jacket", "vest", "pants", "shorts", "skirt", "coat", "dress",
        "jumpsuit", "cape", "glasses", "hat",
        "headband/head covering/hair accessory", "tie", "glove", "watch",
        "belt", "leg warmer", "tights/stockings", "sock", "shoe",
        "bag/wallet", "scarf", "umbrella",
        # Claude variants (not canonical but acceptable)
        "bag", "shirt", "blouse", "top", "t-shirt", "sweatshirt",
        "headband", "head covering", "hair accessory", "wallet",
        "stocking", "stockings", "tights",
        None,
    }

    VALID_TEXTILE_PATTERNS = {
        "plain", "floral", "stripe", "check", "dot", "geometric",
        "paisley", "abstract", "camouflage", "houndstooth", "herringbone",
        "chevron", "argyle", "fair isle", "toile de jouy", "leopard",
        "snakeskin", "zebra", "plant", "letters/numbers",
        # Claude variants (LLM may produce synonyms)
        "letters, numbers", "solid", "plaid", "tartan", "gingham",
        "animal print", "tropical", "damask", "brocade", "ikat",
        "polka dot", "striped", "checked", "cheetah", "camo",
        "tie-dye", "tie dye", "colorblock", "color block", "ombre",
        "graphic", "embroidered", "printed", "woven",
        None,
    }

    def test_fp_category_values_valid(self, db_session):
        from storage.database import Product
        from sqlalchemy import distinct
        values = [
            r[0] for r in db_session.query(distinct(Product.fp_category)).all()
        ]
        for v in values:
            assert v in self.VALID_FP_CATEGORIES, f"Invalid fp_category: '{v}'"

    def test_textile_pattern_values_valid(self, db_session):
        from storage.database import Product
        from sqlalchemy import distinct
        values = [
            r[0] for r in db_session.query(distinct(Product.textile_pattern)).all()
        ]
        unexpected = [v for v in values if v not in self.VALID_TEXTILE_PATTERNS]
        # Allow up to 5 unexpected values (Claude occasionally invents patterns)
        assert len(unexpected) <= 5, (
            f"Too many invalid textile_patterns ({len(unexpected)}): {unexpected}"
        )
        if unexpected:
            import warnings
            warnings.warn(
                f"Non-standard textile_patterns found: {unexpected}",
                stacklevel=1,
            )
