"""
Unit tests for storage/database.py Product model.

Uses in-memory SQLite to test model structure without PostgreSQL.
"""
import pytest
import json
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def in_memory_db():
    """Create an in-memory SQLite database with the Product table.

    NOTE: Skipped — the Product model uses PostgreSQL ARRAY and pgvector
    column types that SQLite cannot compile. Tests that require actual DB
    operations live in tests/data_integrity/ and tests/integration/.
    """
    pytest.skip("Product model uses PostgreSQL-specific ARRAY/pgvector types; SQLite not supported")


class TestProductModel:

    def test_table_name(self):
        from storage.database import Product
        assert Product.__tablename__ == "products"

    def test_all_expected_columns_exist(self):
        from storage.database import Product
        mapper = inspect(Product)
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id", "external_id", "platform", "title", "description",
            "price", "currency", "primary_image", "image_urls",
            "seller_name", "seller_url", "url", "color", "season", "year",
            "era", "decade", "category", "style_tags", "material", "pattern",
            "garment_type", "culture", "period", "object_date",
            "colors", "vibe", "fit_style", "occasion", "ai_description",
            "enriched_text", "fp_category", "silhouette", "neckline",
            "waistline", "length", "sleeve_length", "opening_type",
            "textile_pattern", "textile_finishing", "nickname",
            "garment_parts", "decorations",
            "created_at", "updated_at", "embedded_at", "enriched_at",
        }
        assert expected.issubset(column_names), (
            f"Missing columns: {expected - column_names}"
        )

    def test_create_product_in_memory(self, in_memory_db):
        session, Product = in_memory_db
        p = Product(
            external_id="test-001",
            platform="met_museum",
            title="Test Gown",
            price=0.0,
        )
        session.add(p)
        session.commit()
        assert p.id is not None
        assert p.currency == "USD"

    def test_json_fields_store_and_retrieve(self, in_memory_db):
        session, Product = in_memory_db
        tags = ["dark academia", "gothic"]
        colors = ["black", "burgundy"]
        finishing = ["pleated", "beaded"]

        p = Product(
            external_id="test-002",
            platform="test",
            title="Gothic Dress",
            style_tags=json.dumps(tags),
            colors=json.dumps(colors),
            textile_finishing=json.dumps(finishing),
            garment_parts=json.dumps(["collar", "sleeve"]),
            decorations=json.dumps(["bow"]),
        )
        session.add(p)
        session.commit()

        retrieved = session.query(Product).filter_by(external_id="test-002").first()
        assert json.loads(retrieved.style_tags) == tags
        assert json.loads(retrieved.colors) == colors
        assert json.loads(retrieved.textile_finishing) == finishing

    def test_nullable_fields_accept_none(self, in_memory_db):
        session, Product = in_memory_db
        p = Product(
            external_id="test-003",
            platform="test",
            title="Minimal Product",
        )
        session.add(p)
        session.commit()
        assert p.era is None
        assert p.decade is None
        assert p.fp_category is None
        assert p.enriched_at is None

    def test_external_id_unique(self, in_memory_db):
        session, Product = in_memory_db
        p1 = Product(external_id="dup-001", platform="test", title="First")
        session.add(p1)
        session.commit()

        p2 = Product(external_id="dup-001", platform="test", title="Second")
        session.add(p2)
        with pytest.raises(Exception):
            session.commit()

    def test_timestamps_have_defaults(self, in_memory_db):
        session, Product = in_memory_db
        p = Product(external_id="test-004", platform="test", title="Timestamp Test")
        session.add(p)
        session.commit()
        assert p.created_at is not None
