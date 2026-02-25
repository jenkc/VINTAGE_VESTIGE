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
def require_qdrant(vector_db):
    """Opt-in fixture for tests that need Qdrant."""
    try:
        info = vector_db.get_collection_info()
        for name in ("vintage_images", "vintage_text"):
            assert name in info, f"Missing Qdrant collection: {name}"
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")
