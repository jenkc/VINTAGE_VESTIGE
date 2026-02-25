"""
Integration tests for bridge query utilities against live database.

Validates that query functions return well-formed results
from actual PostgreSQL data.
"""
import pytest
from sqlalchemy import func
from storage.database import SessionLocal, StyleBridge
from analysis.bridge_queries import (
    get_bridges_for_product,
    get_top_bridges,
    get_bridge_detail,
    get_bridge_between,
    get_bridge_stats,
)


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="module")
def bridged_product_id(db):
    """Find a product that has at least one bridge."""
    row = (
        db.query(StyleBridge.source_id)
        .group_by(StyleBridge.source_id)
        .having(func.count() > 5)
        .first()
    )
    if not row:
        pytest.skip("No products with bridges in DB")
    return row[0]


# ---------------------------------------------------------------------------
# get_bridges_for_product
# ---------------------------------------------------------------------------

class TestGetBridgesForProduct:
    def test_returns_bridges(self, db, bridged_product_id):
        result = get_bridges_for_product(db, bridged_product_id, limit=5)
        assert result['total'] > 0
        assert len(result['bridges']) > 0
        assert len(result['bridges']) <= 5

    def test_bridge_structure(self, db, bridged_product_id):
        """Each bridge should have source, target, scores, and metadata."""
        result = get_bridges_for_product(db, bridged_product_id, limit=1)
        b = result['bridges'][0]
        assert 'source' in b
        assert 'target' in b
        assert 'bridge_score' in b
        assert 'bridge_type' in b
        assert 'shared_attributes' in b
        assert isinstance(b['shared_attributes'], dict)

    def test_product_summary_structure(self, db, bridged_product_id):
        """Product summaries should have parsed fields."""
        result = get_bridges_for_product(db, bridged_product_id, limit=1)
        src = result['bridges'][0]['source']
        assert 'id' in src
        assert 'platform' in src
        assert 'title' in src
        assert isinstance(src['style_tags'], list)
        assert isinstance(src['colors'], list)

    def test_pagination_metadata(self, db, bridged_product_id):
        result = get_bridges_for_product(db, bridged_product_id, limit=3, offset=0)
        assert 'total' in result
        assert result['limit'] == 3
        assert result['offset'] == 0

    def test_filter_by_type(self, db, bridged_product_id):
        result = get_bridges_for_product(
            db, bridged_product_id, bridge_type='same_era', limit=50
        )
        for b in result['bridges']:
            assert b['bridge_type'] == 'same_era'

    def test_filter_by_min_score(self, db, bridged_product_id):
        result = get_bridges_for_product(db, bridged_product_id, min_score=0.7, limit=50)
        for b in result['bridges']:
            assert b['bridge_score'] >= 0.7

    def test_nonexistent_product_returns_empty(self, db):
        result = get_bridges_for_product(db, 999999)
        assert result['total'] == 0
        assert result['bridges'] == []

    def test_results_ordered_by_score_desc(self, db, bridged_product_id):
        result = get_bridges_for_product(db, bridged_product_id, limit=10)
        scores = [b['bridge_score'] for b in result['bridges']]
        assert scores == sorted(scores, reverse=True)


# ---------------------------------------------------------------------------
# get_top_bridges
# ---------------------------------------------------------------------------

class TestGetTopBridges:
    def test_returns_bridges(self, db):
        result = get_top_bridges(db, limit=5)
        assert result['total'] > 0
        assert len(result['bridges']) == 5

    def test_ordered_by_score(self, db):
        result = get_top_bridges(db, limit=20)
        scores = [b['bridge_score'] for b in result['bridges']]
        assert scores == sorted(scores, reverse=True)

    def test_filter_by_type(self, db):
        result = get_top_bridges(db, bridge_type='cross_era', limit=10)
        for b in result['bridges']:
            assert b['bridge_type'] == 'cross_era'

    def test_filter_by_score_range(self, db):
        result = get_top_bridges(db, min_score=0.6, max_score=0.8, limit=20)
        for b in result['bridges']:
            assert 0.6 <= b['bridge_score'] <= 0.8

    def test_filter_by_platform(self, db):
        result = get_top_bridges(
            db, source_platform='met_museum', limit=10
        )
        for b in result['bridges']:
            platforms = {b['source']['platform'], b['target']['platform']}
            assert 'met_museum' in platforms

    def test_filter_by_platform_pair(self, db):
        result = get_top_bridges(
            db,
            source_platform='met_museum',
            target_platform='fashionpedia',
            limit=10,
        )
        for b in result['bridges']:
            platforms = {b['source']['platform'], b['target']['platform']}
            assert platforms == {'met_museum', 'fashionpedia'}

    def test_pagination(self, db):
        page1 = get_top_bridges(db, limit=5, offset=0)
        page2 = get_top_bridges(db, limit=5, offset=5)
        ids1 = {b['id'] for b in page1['bridges']}
        ids2 = {b['id'] for b in page2['bridges']}
        assert ids1.isdisjoint(ids2), "Pages should not overlap"


# ---------------------------------------------------------------------------
# get_bridge_detail
# ---------------------------------------------------------------------------

class TestGetBridgeDetail:
    def test_returns_bridge(self, db):
        # Get a known bridge ID first
        top = get_top_bridges(db, limit=1)
        if not top['bridges']:
            pytest.skip("No bridges in DB")
        bridge_id = top['bridges'][0]['id']

        detail = get_bridge_detail(db, bridge_id)
        assert detail is not None
        assert detail['id'] == bridge_id
        assert detail['source']['id'] > 0
        assert detail['target']['id'] > 0

    def test_nonexistent_returns_none(self, db):
        assert get_bridge_detail(db, 999999999) is None


# ---------------------------------------------------------------------------
# get_bridge_between
# ---------------------------------------------------------------------------

class TestGetBridgeBetween:
    def test_finds_existing_bridge(self, db):
        # Get a known pair
        top = get_top_bridges(db, limit=1)
        if not top['bridges']:
            pytest.skip("No bridges in DB")
        b = top['bridges'][0]
        src_id, tgt_id = b['source']['id'], b['target']['id']

        result = get_bridge_between(db, src_id, tgt_id)
        assert result is not None
        assert result['bridge_score'] == b['bridge_score']

    def test_canonical_ordering_transparent(self, db):
        """Querying (A, B) and (B, A) should return the same bridge."""
        top = get_top_bridges(db, limit=1)
        if not top['bridges']:
            pytest.skip("No bridges in DB")
        b = top['bridges'][0]
        src_id, tgt_id = b['source']['id'], b['target']['id']

        forward = get_bridge_between(db, src_id, tgt_id)
        reverse = get_bridge_between(db, tgt_id, src_id)
        assert forward is not None
        assert reverse is not None
        assert forward['id'] == reverse['id']

    def test_no_bridge_returns_none(self, db):
        result = get_bridge_between(db, 999998, 999999)
        assert result is None


# ---------------------------------------------------------------------------
# get_bridge_stats
# ---------------------------------------------------------------------------

class TestGetBridgeStats:
    def test_returns_stats(self, db):
        stats = get_bridge_stats(db)
        assert stats['total_bridges'] > 0
        assert stats['total_products_with_bridges'] > 0
        assert len(stats['by_type']) > 0
        assert len(stats['score_histogram']) == 10

    def test_type_stats_have_required_fields(self, db):
        stats = get_bridge_stats(db)
        for ts in stats['by_type']:
            assert 'bridge_type' in ts
            assert 'count' in ts
            assert 'avg_score' in ts
            assert ts['count'] > 0

    def test_type_counts_sum_to_total(self, db):
        stats = get_bridge_stats(db)
        type_sum = sum(ts['count'] for ts in stats['by_type'])
        assert type_sum == stats['total_bridges']

    def test_histogram_buckets_cover_all(self, db):
        stats = get_bridge_stats(db)
        hist_sum = sum(b['count'] for b in stats['score_histogram'])
        assert hist_sum == stats['total_bridges']

    def test_histogram_bucket_labels(self, db):
        stats = get_bridge_stats(db)
        labels = [b['bucket'] for b in stats['score_histogram']]
        assert labels[0] == '0.0-0.1'
        assert labels[-1] == '0.9-1.0'
