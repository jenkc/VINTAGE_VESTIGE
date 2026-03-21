"""
Comprehensive database integrity tests.

Covers:
  - Product completeness and field validity
  - Vibe vocabulary enforcement
  - Social function canonical values
  - Bridge structural invariants
  - Bridge classifier dimension coverage
  - Narrative generation coverage
  - Near-duplicate detection (same-era + high text_sim bridges should not exist)
  - Cross-reference integrity

Run with: pytest tests/data_integrity/test_db_integrity.py -v
"""
import json
import pytest
from sqlalchemy import text, func


VALID_VIBE_TERMS = {
    # Axis 1 — Volume/Silhouette
    'Exaggerated Volume', 'Column Minimalism', 'Empire Suspension',
    'Constructed Armor', 'Draped Fluidity', 'Layered Accumulation',
    # Axis 2 — Ornament/Surface
    'Maximalist Ornament', 'Austere Restraint', 'Handcraft Visibility',
    'Material Luxury', 'Pattern as Language', 'Transparency and Revelation',
    # Axis 3 — Body Relationship
    'Body Liberation', 'Body Transformation', 'Body Concealment', 'Body Display',
    # Axis 4 — Cultural Register
    'Pastoral Naturalism', 'Ceremonial Formalism', 'Dark Romanticism',
    'Transgressive Subversion', 'Nostalgic Revival', 'Elite Distinction',
}

VALID_SOCIAL_FUNCTIONS = {
    # Canonical clusters
    'ceremonial', 'formal-evening', 'artistic-expression', 'subculture-identity',
    'cultural-heritage', 'festival-celebration', 'leisure-resort',
    # Pass-throughs
    'status-signaling', 'everyday-practical', 'court-formal', 'performance-costume',
    'sportswear', 'workwear', 'military-uniform', 'wedding', 'mourning',
    'academic-formal', 'diplomatic-gift', 'dance', 'maternity',
    # Uncommon but distinct
    'hunting', 'courtship', 'body-shaping', 'body-modification',
    'novelty-gift', 'infant-care', 'medical-adaptive',
}

VALID_BRIDGE_TYPES = {
    # Pass names (passes 2-4)
    'opposition', 'function', 'structural',
    # Pass 1 stores temporal type classification directly as bridge_type
    'transmission', 'continuation', 'echo', 'cross_vibe',
    # Legacy / edge cases
    'similarity', 'cross_category', 'cross_culture',
}

VALID_TEMPORAL_TYPES = {
    'echo', 'transmission', 'continuation', 'cross_vibe', 'contemporary',
}

VALID_CROSSING_TYPES = {
    'same_context', 'cross_category', 'cross_culture', 'cross_category_culture',
}

VALID_CONNECTION_MODES = {
    'contrast', 'resonance', 'affinity',
}

VALID_PLATFORMS = {
    'met_museum', 'smithsonian', 'fashionpedia', 'va_museum',
}


@pytest.fixture(scope="module")
def db():
    from storage.database import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


# ---------------------------------------------------------------------------
# Products — completeness
# ---------------------------------------------------------------------------

class TestProductCompleteness:

    def test_total_product_count(self, db):
        """Expect ~4234 products."""
        count = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
        assert count >= 4000, f"Only {count} products — expected ~4234"

    def test_all_products_enriched(self, db):
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE enriched_at IS NULL"
        )).scalar()
        assert count == 0, f"{count} products not enriched"

    def test_all_products_have_era(self, db):
        """Most products should have era — allow ≤10 for undatable accessories."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE era IS NULL OR era = ''"
        )).scalar()
        assert count <= 10, f"{count} products missing era (expected ≤10)"

    def test_all_products_have_fp_category(self, db):
        """Most products should have fp_category — museum items may not map to Fashionpedia."""
        total = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE fp_category IS NULL OR fp_category = ''"
        )).scalar()
        pct = count / total * 100
        assert pct < 5, f"{count} products ({pct:.1f}%) missing fp_category — expected <5%"

    def test_all_products_have_embeddings(self, db):
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE text_embedding IS NULL"
        )).scalar()
        assert count == 0, f"{count} products missing text_embedding"

    def test_platform_values_valid(self, db):
        rows = db.execute(text(
            "SELECT DISTINCT platform FROM products"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_PLATFORMS
        assert not invalid, f"Unknown platforms: {invalid}"

    def test_core_vibes_coverage(self, db):
        """Most enriched products should have core_vibes."""
        total = db.execute(text("SELECT COUNT(*) FROM products")).scalar()
        missing = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE core_vibes IS NULL OR array_length(core_vibes, 1) IS NULL"
        )).scalar()
        pct_missing = missing / total * 100
        assert pct_missing < 5, (
            f"{missing}/{total} products ({pct_missing:.1f}%) missing core_vibes — expected <5%"
        )


# ---------------------------------------------------------------------------
# Vibe vocabulary enforcement
# ---------------------------------------------------------------------------

class TestVibeVocabulary:

    def test_core_vibes_only_valid_terms(self, db):
        """All core_vibes values must be from the controlled vocabulary."""
        rows = db.execute(text(
            "SELECT DISTINCT value FROM products, unnest(core_vibes) AS value "
            "WHERE core_vibes IS NOT NULL AND array_length(core_vibes, 1) > 0"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_VIBE_TERMS
        assert not invalid, (
            f"Invalid core_vibes terms found ({len(invalid)}): {sorted(invalid)}"
        )

    def test_bridge_vibes_only_valid_terms(self, db):
        """All bridge_vibes values must be from the controlled vocabulary."""
        rows = db.execute(text(
            "SELECT DISTINCT value FROM products, unnest(bridge_vibes) AS value "
            "WHERE bridge_vibes IS NOT NULL AND array_length(bridge_vibes, 1) > 0"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_VIBE_TERMS
        assert not invalid, (
            f"Invalid bridge_vibes terms found ({len(invalid)}): {sorted(invalid)}"
        )

    def test_core_vibes_max_3_terms(self, db):
        """core_vibes should have at most 3 terms per product."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE array_length(core_vibes, 1) > 3"
        )).scalar()
        assert count == 0, f"{count} products have >3 core_vibes terms"

    def test_bridge_vibes_max_2_terms(self, db):
        """bridge_vibes should have at most 2 terms per product."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM products WHERE array_length(bridge_vibes, 1) > 2"
        )).scalar()
        assert count == 0, f"{count} products have >2 bridge_vibes terms"


# ---------------------------------------------------------------------------
# Social function canonical values
# ---------------------------------------------------------------------------

class TestSocialFunction:

    def test_social_function_only_canonical_values(self, db):
        """All social_function values must be from the canonical set."""
        rows = db.execute(text(
            "SELECT DISTINCT value FROM products, "
            "jsonb_array_elements_text(social_function::jsonb) AS value "
            "WHERE social_function IS NOT NULL"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_SOCIAL_FUNCTIONS
        assert not invalid, (
            f"Non-canonical social_function values ({len(invalid)}): {sorted(invalid)}"
        )

    def test_no_none_in_social_function(self, db):
        """'none' should not appear as a social_function value."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM products "
            "WHERE social_function::jsonb @> '\"none\"'"
        )).scalar()
        assert count == 0, f"{count} products still have 'none' in social_function"


# ---------------------------------------------------------------------------
# Bridge structural invariants
# ---------------------------------------------------------------------------

class TestBridgeInvariants:

    def test_bridge_count_meaningful(self, db):
        count = db.execute(text("SELECT COUNT(*) FROM style_bridges")).scalar()
        assert count >= 10000, f"Only {count} bridges — expected 10000+"

    def test_no_self_referencing_bridges(self, db):
        count = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges WHERE source_id = target_id"
        )).scalar()
        assert count == 0, f"{count} self-referencing bridges"

    def test_canonical_ordering(self, db):
        count = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges WHERE source_id >= target_id"
        )).scalar()
        assert count == 0, f"{count} bridges violate canonical ordering (source_id >= target_id)"

    def test_no_duplicate_pairs(self, db):
        total = db.execute(text("SELECT COUNT(*) FROM style_bridges")).scalar()
        distinct = db.execute(text(
            "SELECT COUNT(*) FROM (SELECT DISTINCT source_id, target_id FROM style_bridges) t"
        )).scalar()
        assert total == distinct, f"{total - distinct} duplicate bridge pairs"

    def test_all_bridge_products_exist(self, db):
        orphans = db.execute(text("""
            SELECT COUNT(*) FROM style_bridges b
            WHERE NOT EXISTS (SELECT 1 FROM products WHERE id = b.source_id)
               OR NOT EXISTS (SELECT 1 FROM products WHERE id = b.target_id)
        """)).scalar()
        assert orphans == 0, f"{orphans} bridges reference non-existent products"

    def test_scores_in_valid_range(self, db):
        for col in ('text_similarity', 'structural_score'):
            bad = db.execute(text(
                f"SELECT COUNT(*) FROM style_bridges "
                f"WHERE {col} IS NOT NULL AND ({col} < 0 OR {col} > 1)"
            )).scalar()
            assert bad == 0, f"{bad} bridges with {col} outside [0, 1]"

    def test_bridge_type_values_valid(self, db):
        rows = db.execute(text(
            "SELECT DISTINCT bridge_type FROM style_bridges WHERE bridge_type IS NOT NULL"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_BRIDGE_TYPES
        assert not invalid, f"Unknown bridge_type values: {invalid}"

    def test_shared_attributes_valid_json(self, db):
        rows = db.execute(text(
            "SELECT id, shared_attributes FROM style_bridges "
            "WHERE shared_attributes IS NOT NULL LIMIT 500"
        )).fetchall()
        bad = []
        for bridge_id, attrs in rows:
            try:
                json.loads(attrs)
            except (json.JSONDecodeError, TypeError):
                bad.append(bridge_id)
        assert not bad, f"{len(bad)} bridges have invalid JSON in shared_attributes"


# ---------------------------------------------------------------------------
# Bridge classifier dimensions
# ---------------------------------------------------------------------------

class TestBridgeClassification:

    def test_all_bridges_classified(self, db):
        """All bridges should have connection_mode set."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges WHERE connection_mode IS NULL"
        )).scalar()
        assert count == 0, f"{count} bridges missing connection_mode"

    def test_temporal_type_coverage(self, db):
        """Most bridges should have temporal_type set."""
        total = db.execute(text("SELECT COUNT(*) FROM style_bridges")).scalar()
        missing = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges WHERE temporal_type IS NULL"
        )).scalar()
        pct = missing / total * 100
        assert pct < 1, f"{missing} bridges ({pct:.1f}%) missing temporal_type"

    def test_connection_mode_values_valid(self, db):
        rows = db.execute(text(
            "SELECT DISTINCT connection_mode FROM style_bridges WHERE connection_mode IS NOT NULL"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_CONNECTION_MODES
        assert not invalid, f"Unknown connection_mode values: {invalid}"

    def test_temporal_type_values_valid(self, db):
        rows = db.execute(text(
            "SELECT DISTINCT temporal_type FROM style_bridges WHERE temporal_type IS NOT NULL"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_TEMPORAL_TYPES
        assert not invalid, f"Unknown temporal_type values: {invalid}"

    def test_crossing_type_values_valid(self, db):
        rows = db.execute(text(
            "SELECT DISTINCT crossing_type FROM style_bridges WHERE crossing_type IS NOT NULL"
        )).fetchall()
        found = {r[0] for r in rows}
        invalid = found - VALID_CROSSING_TYPES
        assert not invalid, f"Unknown crossing_type values: {invalid}"

    def test_contrast_bridges_have_contrast_pair(self, db):
        """Bridges with connection_mode=contrast should have contrast_pair set."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges "
            "WHERE connection_mode = 'contrast' AND contrast_pair IS NULL"
        )).scalar()
        assert count == 0, f"{count} contrast bridges missing contrast_pair"

    def test_connection_mode_distribution_reasonable(self, db):
        """No single connection_mode should account for >90% of bridges."""
        rows = db.execute(text(
            "SELECT connection_mode, COUNT(*) as cnt FROM style_bridges "
            "GROUP BY connection_mode ORDER BY cnt DESC"
        )).fetchall()
        total = sum(r[1] for r in rows)
        for mode, cnt in rows:
            pct = cnt / total * 100
            assert pct < 90, (
                f"connection_mode '{mode}' is {pct:.1f}% of bridges — suspiciously dominant"
            )


# ---------------------------------------------------------------------------
# Narrative coverage
# ---------------------------------------------------------------------------

class TestNarratives:

    def test_narrative_coverage(self, db):
        """At least 90% of bridges should have narratives."""
        total = db.execute(text("SELECT COUNT(*) FROM style_bridges")).scalar()
        with_narrative = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges WHERE bridge_narrative IS NOT NULL"
        )).scalar()
        pct = with_narrative / total * 100
        assert pct >= 90, (
            f"Only {with_narrative}/{total} bridges ({pct:.1f}%) have narratives — expected 90%+"
        )

    def test_narratives_not_truncated(self, db):
        """Narratives should be at least 30 characters (not empty stubs)."""
        count = db.execute(text(
            "SELECT COUNT(*) FROM style_bridges "
            "WHERE bridge_narrative IS NOT NULL AND length(bridge_narrative) < 30"
        )).scalar()
        assert count == 0, f"{count} suspiciously short narratives (< 30 chars)"

    def test_contrast_narratives_longer(self, db):
        """Contrast narratives (2 sentences) should be longer than affinity (1 sentence)."""
        avg_contrast = db.execute(text(
            "SELECT AVG(length(bridge_narrative)) FROM style_bridges "
            "WHERE connection_mode = 'contrast' AND bridge_narrative IS NOT NULL"
        )).scalar()
        avg_affinity = db.execute(text(
            "SELECT AVG(length(bridge_narrative)) FROM style_bridges "
            "WHERE connection_mode = 'affinity' AND bridge_narrative IS NOT NULL"
        )).scalar()
        if avg_contrast and avg_affinity:
            assert avg_contrast > avg_affinity, (
                f"Contrast avg length ({avg_contrast:.0f}) not longer than affinity ({avg_affinity:.0f})"
            )


# ---------------------------------------------------------------------------
# Near-duplicate detection
# ---------------------------------------------------------------------------

class TestNearDuplicates:

    def test_no_same_title_bridges(self, db):
        """No bridge should connect two products with the same title."""
        count = db.execute(text("""
            SELECT COUNT(*) FROM style_bridges b
            JOIN products src ON src.id = b.source_id
            JOIN products tgt ON tgt.id = b.target_id
            WHERE LOWER(TRIM(src.title)) = LOWER(TRIM(tgt.title))
        """)).scalar()
        assert count == 0, f"{count} bridges connect products with identical titles"

    def test_no_same_era_very_high_text_sim(self, db):
        """Same-era bridges with text_similarity >= 0.95 should not exist (near-duplicates)."""
        count = db.execute(text("""
            SELECT COUNT(*) FROM style_bridges b
            JOIN products src ON src.id = b.source_id
            JOIN products tgt ON tgt.id = b.target_id
            WHERE LOWER(TRIM(src.era)) = LOWER(TRIM(tgt.era))
              AND b.text_similarity >= 0.95
        """)).scalar()
        assert count == 0, (
            f"{count} same-era bridges with text_similarity >= 0.95 (likely near-duplicates)"
        )


# ---------------------------------------------------------------------------
# Platform distribution
# ---------------------------------------------------------------------------

class TestPlatformDistribution:

    def test_all_platforms_have_bridges(self, db):
        """Every platform should participate in at least some bridges."""
        rows = db.execute(text("""
            SELECT p.platform, COUNT(DISTINCT b.id) as cnt
            FROM products p
            JOIN (
                SELECT source_id AS pid, id FROM style_bridges
                UNION ALL
                SELECT target_id AS pid, id FROM style_bridges
            ) b ON b.pid = p.id
            GROUP BY p.platform
        """)).fetchall()
        platform_counts = {r[0]: r[1] for r in rows}
        for platform in VALID_PLATFORMS:
            assert platform in platform_counts, f"Platform {platform} has no bridges"
            assert platform_counts[platform] >= 100, (
                f"Platform {platform} only has {platform_counts[platform]} bridges"
            )

    def test_cross_platform_bridges_exist(self, db):
        """At least 30% of bridges should connect different platforms."""
        total = db.execute(text("SELECT COUNT(*) FROM style_bridges")).scalar()
        cross = db.execute(text("""
            SELECT COUNT(*) FROM style_bridges b
            JOIN products src ON src.id = b.source_id
            JOIN products tgt ON tgt.id = b.target_id
            WHERE src.platform != tgt.platform
        """)).scalar()
        pct = cross / total * 100
        assert pct >= 30, f"Only {pct:.1f}% of bridges cross platforms — expected 30%+"
