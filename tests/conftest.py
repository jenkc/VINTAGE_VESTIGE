"""
Root conftest.py — shared fixtures for the entire test suite.

Session-scoped fixtures avoid re-loading models or reconnecting
to databases on every test function.
"""
import pytest
import os
import sys

# Ensure project root is on sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def pytest_collection_modifyitems(config, items):
    """Auto-apply markers based on test file path."""
    for item in items:
        path = str(item.fspath)
        if "/unit/" in path:
            item.add_marker(pytest.mark.unit)
        elif "/integration/" in path:
            item.add_marker(pytest.mark.integration)
        elif "/data_integrity/" in path:
            item.add_marker(pytest.mark.data_integrity)
        elif "/search_quality/" in path:
            item.add_marker(pytest.mark.slow)


# ---------------------------------------------------------------------------
# Session-scoped: Embedding models (heavy, ~30s to load)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def embedding_generator():
    """EmbeddingGenerator instance (loads CLIP + MiniLM once per session)."""
    from embeddings.generator import EmbeddingGenerator
    return EmbeddingGenerator()


# ---------------------------------------------------------------------------
# Session-scoped: Database session (live PostgreSQL)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def db_session():
    """SQLAlchemy session for the test run."""
    from storage.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Session-scoped: pgvector search
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def vector_search(db_session):
    """VectorSearch instance using the test DB session."""
    from storage.vector_search import VectorSearch
    return VectorSearch(db_session)


# ---------------------------------------------------------------------------
# Sample data fixtures (no DB required)
# ---------------------------------------------------------------------------
@pytest.fixture
def sample_product_data():
    """Minimal product dict for unit tests."""
    return {
        "title": "Silk Evening Gown",
        "description": "A stunning floor-length silk evening gown from the 1920s",
        "category": "dress",
        "primary_image": None,
        "price": 0.0,
        "platform": "met_museum",
    }


@pytest.fixture
def sample_enrichment():
    """Full enrichment result dict for unit tests."""
    return {
        "fp_category": "dress",
        "nickname": "gown",
        "silhouette": "a-line",
        "neckline": "v-neck",
        "waistline": "empire waistline",
        "length": "floor length",
        "sleeve_length": "sleeveless",
        "opening_type": None,
        "textile_pattern": "plain",
        "textile_finishing": ["beaded"],
        "garment_parts": ["neckline", "sleeve"],
        "decorations": ["sequin"],
        "era": "Art Deco",
        "decade": "1920s",
        "style_tags": ["glamorous", "old money", "gatsby"],
        "colors": ["champagne", "gold"],
        "material": "silk charmeuse",
        "season": "evening",
        "garment_type": "beaded evening gown",
        "vibe": "great gatsby glamour",
        "fit_style": "bias cut flowing",
        "occasion": "formal evening",
        "ai_description": (
            "A luminous 1920s silk charmeuse evening gown with Art Deco beading. "
            "Channels the glamour of a Fitzgerald party with its bias-cut silhouette "
            "and champagne-gold shimmer."
        ),
    }


@pytest.fixture
def minimal_enrichment():
    """Enrichment dict with many None/empty fields for edge-case testing."""
    return {
        "fp_category": None,
        "nickname": None,
        "silhouette": None,
        "neckline": None,
        "waistline": None,
        "length": None,
        "sleeve_length": None,
        "opening_type": None,
        "textile_pattern": "plain",
        "textile_finishing": [],
        "garment_parts": [],
        "decorations": [],
        "era": "Modern",
        "decade": None,
        "style_tags": ["casual", "everyday"],
        "colors": ["unknown"],
        "material": "unknown",
        "season": "all-season",
        "garment_type": "shirt",
        "vibe": "casual comfortable",
        "fit_style": "standard",
        "occasion": "everyday",
        "ai_description": "A casual shirt for everyday wear",
    }
