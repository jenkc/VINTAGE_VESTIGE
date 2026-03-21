"""
Data integrity tests for the style bridge system.

Validates bridge data quality, deduplication invariants,
and structural consistency:
  - Canonical ordering (source_id < target_id)
  - No self-referencing bridges
  - No duplicate pairs
  - Narrative generation
"""
import json
import pytest
from storage.database import SessionLocal, Product, StyleBridge
from sqlalchemy import func


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Bridge invariants
# ---------------------------------------------------------------------------

class TestBridgeInvariants:
    """Core invariants that must always hold."""

    def test_no_self_referencing_bridges(self, db):
        """No bridge should have source_id == target_id."""
        count = (
            db.query(StyleBridge)
            .filter(StyleBridge.source_id == StyleBridge.target_id)
            .count()
        )
        assert count == 0, f"Found {count} self-referencing bridges"

    def test_canonical_ordering(self, db):
        """All bridges must have source_id < target_id."""
        bad = (
            db.query(StyleBridge)
            .filter(StyleBridge.source_id >= StyleBridge.target_id)
            .count()
        )
        assert bad == 0, f"Found {bad} bridges violating canonical order (source_id >= target_id)"

    def test_no_duplicate_pairs(self, db):
        """Each (source_id, target_id) pair appears exactly once."""
        total = db.query(func.count(StyleBridge.id)).scalar()
        distinct = (
            db.query(func.count())
            .select_from(
                db.query(StyleBridge.source_id, StyleBridge.target_id)
                .distinct()
                .subquery()
            )
            .scalar()
        )
        assert total == distinct, (
            f"Found {total - distinct} duplicate bridge pairs"
        )

    def test_all_bridge_products_exist(self, db):
        """Every source_id and target_id references a real product."""
        product_ids = set(r[0] for r in db.query(Product.id).all())
        bridges = db.query(StyleBridge.source_id, StyleBridge.target_id).all()
        orphans = []
        for src, tgt in bridges:
            if src not in product_ids:
                orphans.append(f"source={src}")
            if tgt not in product_ids:
                orphans.append(f"target={tgt}")
        assert len(orphans) == 0, (
            f"Found {len(orphans)} orphaned bridge references: {orphans[:5]}"
        )


# ---------------------------------------------------------------------------
# Bridge data quality
# ---------------------------------------------------------------------------

class TestBridgeDataQuality:
    """Bridge scores and metadata should be well-formed."""

    def test_component_scores_in_valid_range(self, db):
        """All component scores should be between 0 and 1."""
        for col_name, col in [('text_similarity', StyleBridge.text_similarity),
                               ('structural_score', StyleBridge.structural_score)]:
            bad = db.query(StyleBridge).filter((col < 0) | (col > 1)).count()
            assert bad == 0, f"Found {bad} bridges with {col_name} outside [0, 1]"

    def test_text_similarity_in_valid_range(self, db):
        """text_similarity should be between 0 and 1."""
        bad = (
            db.query(StyleBridge)
            .filter(
                (StyleBridge.text_similarity < 0)
                | (StyleBridge.text_similarity > 1)
            )
            .count()
        )
        assert bad == 0, f"Found {bad} bridges with text_similarity outside [0, 1]"

    def test_structural_score_in_valid_range(self, db):
        """structural_score should be between 0 and 1."""
        bad = (
            db.query(StyleBridge)
            .filter(
                (StyleBridge.structural_score < 0)
                | (StyleBridge.structural_score > 1)
            )
            .count()
        )
        assert bad == 0, f"Found {bad} bridges with structural_score outside [0, 1]"

    def test_bridge_type_values_valid(self, db):
        """bridge_type should be one of the known types."""
        valid_types = {
            # Pass 1 (temporal)
            'transmission', 'continuation', 'echo', 'cross_vibe', 'contemporary',
            # Pass 2 (opposition)
            'opposition',
            # Pass 3 (shared purpose)
            'function',
            # Pass 4 (structural)
            'structural',
            # Legacy types (may still exist in DB)
            'revival', 'cross_category', 'cross_culture', 'near_era',
        }
        types_in_db = set(
            r[0] for r in db.query(StyleBridge.bridge_type).distinct().all()
            if r[0] is not None
        )
        invalid = types_in_db - valid_types
        assert len(invalid) == 0, f"Unknown bridge types: {invalid}"

    def test_shared_attributes_is_valid_json(self, db):
        """shared_attributes should be parseable JSON."""
        bridges = (
            db.query(StyleBridge.id, StyleBridge.shared_attributes)
            .filter(StyleBridge.shared_attributes != None)
            .limit(200)
            .all()
        )
        bad = []
        for bridge_id, attrs in bridges:
            try:
                json.loads(attrs)
            except (json.JSONDecodeError, TypeError):
                bad.append(bridge_id)
        assert len(bad) == 0, f"Found {len(bad)} bridges with invalid JSON shared_attributes"


# ---------------------------------------------------------------------------
# Bridge coverage
# ---------------------------------------------------------------------------

class TestBridgeCoverage:
    """Bridge distribution across platforms and types."""

    def test_bridges_exist(self, db):
        """There should be a meaningful number of bridges."""
        count = db.query(func.count(StyleBridge.id)).scalar()
        assert count >= 1000, f"Only {count} bridges — expected 1000+"

    def test_all_bridge_types_represented(self, db):
        """Each pipeline pass should have produced some bridges."""
        expected_types = {'transmission', 'function', 'structural'}
        types_in_db = set(
            r[0] for r in db.query(StyleBridge.bridge_type).distinct().all()
            if r[0] is not None
        )
        missing = expected_types - types_in_db
        assert len(missing) == 0, f"Missing bridge types: {missing}"

    def test_transmission_bridges_span_platforms(self, db):
        """transmission bridges should connect different platforms."""
        transmission = (
            db.query(StyleBridge)
            .filter(StyleBridge.bridge_type == 'transmission')
            .limit(50)
            .all()
        )
        if not transmission:
            pytest.skip("No transmission bridges")

        product_ids = set()
        for b in transmission:
            product_ids.add(b.source_id)
            product_ids.add(b.target_id)

        products = db.query(Product.id, Product.platform).filter(
            Product.id.in_(product_ids)
        ).all()
        platforms = set(p.platform for p in products)
        assert len(platforms) >= 2, (
            f"transmission bridges only touch {platforms} — expected 2+ platforms"
        )


