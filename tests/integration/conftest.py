"""Integration test fixtures — verify infrastructure is available."""
import pytest


@pytest.fixture(scope="session", autouse=True)
def check_postgres(db_session):
    """Fail fast if PostgreSQL is not reachable."""
    try:
        from storage.database import Product
        count = db_session.query(Product).count()
        assert count > 0, f"Database has {count} products; expected >0"
    except Exception as e:
        pytest.skip(f"PostgreSQL not available: {e}")


@pytest.fixture(scope="session")
def require_vectors(db_session):
    """Opt-in fixture for tests that need pgvector embeddings."""
    try:
        from sqlalchemy import text
        count = db_session.execute(
            text("SELECT COUNT(*) FROM products WHERE text_embedding IS NOT NULL")
        ).scalar()
        assert count > 0, "No text embeddings found in products table"
    except Exception as e:
        pytest.skip(f"pgvector not available: {e}")
