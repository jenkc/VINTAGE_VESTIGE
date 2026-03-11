"""
Tests for multi-dimensional bridge classification.

Tests the classifier in scripts/classify_bridge_dimensions.py which replaces
the old single-column semantic_type with 6 orthogonal dimensions:
  temporal_type, crossing_type, connection_mode, primary_axis, secondary_axis, contrast_pair
"""
import json
import pytest
from types import SimpleNamespace


# ---------------------------------------------------------------------------
# Helpers — fake product and bridge objects for testing
# ---------------------------------------------------------------------------

def make_product(**kwargs):
    """Create a minimal product-like object for classification tests."""
    defaults = {
        'id': 1,
        'era': None,
        'decade': None,
        'platform': 'met_museum',
        'fp_category': None,
        'culture': None,
        'core_vibes': [],
        'bridge_vibes': [],
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def make_bridge(**kwargs):
    """Create a minimal bridge-like object for classification tests."""
    defaults = {
        'id': 1,
        'source_id': 1,
        'target_id': 2,
        'bridge_type': 'transmission',
        'text_similarity': 0.7,
        'image_similarity': 0.5,
        'structural_score': 0.4,
        'connection_mode': None,
        'shared_attributes': '{}',
        'temporal_type': None,  # will be set during classification
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


# ===========================================================================
# TEMPORAL TYPE TESTS
# ===========================================================================

class TestClassifyTemporalType:

    def test_echo_from_very_distant_eras(self):
        """Very distant named eras (80+ yr gap) → echo."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            'Victorian Late / Bustle', 'Quiet Luxury',
            'met_museum', 'fashionpedia')
        assert result == 'echo'

    def test_continuation_same_era_distant_decades(self):
        """Same era, decades 20+ years apart → continuation."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            'Victorian Late / Bustle', 'Victorian Late / Bustle',
            'met_museum', 'met_museum',
            '1870s', '1890s')
        assert result == 'continuation'

    def test_cross_category_with_distant_eras(self):
        """Cross-category bridges compute temporal from era distance."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            'Victorian Late / Bustle', 'Quiet Luxury',
            'met_museum', 'fashionpedia')
        assert result == 'echo'

    def test_cross_category_with_close_eras(self):
        """Close eras → continuation or contemporary."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            'Atomic Age', 'Space Age',
            'met_museum', 'met_museum',
            '1950s', '1960s')
        assert result in ('continuation', 'contemporary')

    def test_same_era_close_decades_is_contemporary(self):
        """Same era, close decades → contemporary."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            'Minimalism', 'Minimalism',
            'fashionpedia', 'fashionpedia',
            '1990s', '1990s')
        assert result == 'contemporary'

    def test_platform_fallback(self):
        """No era data → use platform proxy."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            None, None,
            'met_museum', 'fashionpedia')
        assert result == 'transmission'

    def test_both_modern_platforms_no_era_returns_none(self):
        """Same platform type with no eras/decades → None (unknown)."""
        from tools.analysis.classify_bridge_dimensions import classify_temporal_type
        result = classify_temporal_type(
            None, None,
            'fashionpedia', 'fashionpedia')
        assert result is None


# ===========================================================================
# CROSSING TYPE TESTS
# ===========================================================================

class TestClassifyCrossingType:

    def test_same_context(self):
        """Same category group + same culture → same_context."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category='dress', culture='Western')
        tgt = make_product(fp_category='gown', culture='Western')
        assert classify_crossing_type(src, tgt) == 'same_context'

    def test_cross_category(self):
        """Different category groups → cross_category."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category='dress', culture='Western')
        tgt = make_product(fp_category='jacket', culture='Western')
        assert classify_crossing_type(src, tgt) == 'cross_category'

    def test_cross_culture(self):
        """Same category, different culture → cross_culture."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category='dress', culture='Japanese')
        tgt = make_product(fp_category='gown', culture='Western')
        assert classify_crossing_type(src, tgt) == 'cross_culture'

    def test_cross_category_culture(self):
        """Different category AND different culture → cross_category_culture."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category='coat', culture='Japanese')
        tgt = make_product(fp_category='dress', culture='Western')
        assert classify_crossing_type(src, tgt) == 'cross_category_culture'

    def test_null_category_is_same_context(self):
        """Null categories → same_context (can't determine crossing)."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category=None, culture=None)
        tgt = make_product(fp_category=None, culture=None)
        assert classify_crossing_type(src, tgt) == 'same_context'

    def test_case_insensitive_culture(self):
        """Culture comparison is case-insensitive."""
        from tools.analysis.classify_bridge_dimensions import classify_crossing_type
        src = make_product(fp_category='dress', culture='western')
        tgt = make_product(fp_category='gown', culture='Western')
        assert classify_crossing_type(src, tgt) == 'same_context'


# ===========================================================================
# CONTRAST DETECTION TESTS
# ===========================================================================

class TestDetectContrast:

    def test_volume_opposition(self):
        """Exaggerated Volume vs Column Minimalism triggers contrast."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        src_vibes = {'Exaggerated Volume', 'Maximalist Ornament'}
        tgt_vibes = {'Column Minimalism', 'Austere Restraint'}
        result = _detect_contrast(src_vibes, tgt_vibes, structural_score=0.5)
        assert result is not None
        pair_str, axis = result
        assert 'Exaggerated Volume' in pair_str
        assert 'Column Minimalism' in pair_str

    def test_body_opposition(self):
        """Body Display vs Body Concealment triggers contrast."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        src_vibes = {'Body Display'}
        tgt_vibes = {'Body Concealment'}
        result = _detect_contrast(src_vibes, tgt_vibes, structural_score=0.5)
        assert result is not None
        _, axis = result
        assert axis == 'body'

    def test_register_opposition(self):
        """Transgressive Subversion vs Elite Distinction triggers contrast."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        src_vibes = {'Transgressive Subversion'}
        tgt_vibes = {'Elite Distinction'}
        result = _detect_contrast(src_vibes, tgt_vibes, structural_score=0.5)
        assert result is not None
        _, axis = result
        assert axis == 'register'

    def test_body_concealment_triple_opposition(self):
        """Body Concealment participates in multiple pairs."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        # Pair 5: Transparency and Revelation ↔ Body Concealment
        result1 = _detect_contrast(
            {'Transparency and Revelation'}, {'Body Concealment'}, 0.5)
        assert result1 is not None

        # Pair 7: Body Display ↔ Body Concealment
        result2 = _detect_contrast(
            {'Body Display'}, {'Body Concealment'}, 0.5)
        assert result2 is not None

    def test_structural_gate_blocks(self):
        """Low structural score blocks contrast detection."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        src_vibes = {'Exaggerated Volume'}
        tgt_vibes = {'Column Minimalism'}
        result = _detect_contrast(src_vibes, tgt_vibes, structural_score=0.2)
        assert result is None

    def test_no_opposition_returns_none(self):
        """Non-opposing vibes return None."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        src_vibes = {'Exaggerated Volume', 'Maximalist Ornament'}
        tgt_vibes = {'Layered Accumulation', 'Handcraft Visibility'}
        result = _detect_contrast(src_vibes, tgt_vibes, structural_score=0.5)
        assert result is None

    def test_same_vibes_no_contrast(self):
        """Shared vibes are not opposition."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        vibes = {'Body Liberation', 'Pastoral Naturalism'}
        result = _detect_contrast(vibes, vibes, structural_score=0.5)
        assert result is None

    def test_reversed_order_still_detects(self):
        """Opposition detected regardless of which product holds which vibe."""
        from tools.analysis.classify_bridge_dimensions import _detect_contrast
        r1 = _detect_contrast(
            {'Constructed Armor'}, {'Draped Fluidity'}, 0.5)
        r2 = _detect_contrast(
            {'Draped Fluidity'}, {'Constructed Armor'}, 0.5)
        assert r1 is not None
        assert r2 is not None


# ===========================================================================
# CONNECTION MODE TESTS
# ===========================================================================

class TestClassifyConnectionMode:

    def test_resonance_detection(self):
        """Resonance detected when text_sim > 0.85 + transmission."""
        from tools.analysis.classify_bridge_dimensions import classify_connection_mode
        bridge = make_bridge(
            text_similarity=0.90,
            structural_score=0.5,
            shared_attributes=json.dumps({'material': 'silk'}),
        )
        bridge.temporal_type = 'transmission'
        src = make_product(core_vibes=['Nostalgic Revival', 'Maximalist Ornament'])
        tgt = make_product(core_vibes=['Maximalist Ornament'])
        mode, primary, secondary, pair = classify_connection_mode(bridge, src, tgt)
        assert mode == 'resonance'
        assert pair is None  # no contrast pair for resonance

    def test_contrast_before_resonance(self):
        """Contrast takes priority over resonance when both conditions met."""
        from tools.analysis.classify_bridge_dimensions import classify_connection_mode
        bridge = make_bridge(
            text_similarity=0.6,
            structural_score=0.5,
            shared_attributes=json.dumps({'construction_technique': ['hand-embroidery']}),
        )
        bridge.temporal_type = 'transmission'
        src = make_product(core_vibes=['Exaggerated Volume'])
        tgt = make_product(core_vibes=['Column Minimalism'])
        mode, primary, secondary, pair = classify_connection_mode(bridge, src, tgt)
        assert mode == 'contrast'
        assert pair is not None

    def test_contrast_beats_resonance(self):
        """Contrast wins even with text_sim > 0.85 + transmission."""
        from tools.analysis.classify_bridge_dimensions import classify_connection_mode
        bridge = make_bridge(
            text_similarity=0.90,
            structural_score=0.5,
            shared_attributes=json.dumps({'material': 'silk'}),
        )
        bridge.temporal_type = 'transmission'
        src = make_product(core_vibes=['Exaggerated Volume'])
        tgt = make_product(core_vibes=['Column Minimalism'])
        mode, primary, secondary, pair = classify_connection_mode(bridge, src, tgt)
        assert mode == 'contrast'
        assert pair is not None

    def test_affinity_fallback(self):
        """Affinity is the default when no other mode matches."""
        from tools.analysis.classify_bridge_dimensions import classify_connection_mode
        bridge = make_bridge(
            text_similarity=0.7,
            image_similarity=0.6,
            structural_score=0.35,
            shared_attributes=json.dumps({'silhouette': 'a-line'}),
        )
        bridge.temporal_type = 'contemporary'
        src = make_product(core_vibes=['Layered Accumulation'])
        tgt = make_product(core_vibes=['Handcraft Visibility'])
        mode, _, _, _ = classify_connection_mode(bridge, src, tgt)
        assert mode == 'affinity'

    def test_empty_vibes_defaults_affinity(self):
        """Products with no core_vibes get affinity."""
        from tools.analysis.classify_bridge_dimensions import classify_connection_mode
        bridge = make_bridge(
            text_similarity=0.7,
            structural_score=0.5,
            shared_attributes=json.dumps({'silhouette': 'a-line'}),
        )
        bridge.temporal_type = 'transmission'
        src = make_product(core_vibes=None)
        tgt = make_product(core_vibes=None)
        mode, _, _, _ = classify_connection_mode(bridge, src, tgt)
        assert mode == 'affinity'


# ===========================================================================
# AXIS DERIVATION TESTS
# ===========================================================================

class TestDeriveAxes:

    def test_silhouette_is_volume(self):
        """Shared silhouette → primary axis is volume."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        primary, secondary = _derive_axes_from_shared({'silhouette': 'empire'})
        assert primary == 'volume'

    def test_material_is_ornament(self):
        """Shared material → primary axis is ornament."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        primary, _ = _derive_axes_from_shared({'material': 'silk'})
        assert primary == 'ornament'

    def test_neckline_is_body(self):
        """Shared neckline → primary axis is body."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        primary, _ = _derive_axes_from_shared({'neckline': 'v-neck'})
        assert primary == 'body'

    def test_social_function_is_register(self):
        """Shared social_function → primary axis is register."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        primary, _ = _derive_axes_from_shared({'social_function': ['wedding']})
        assert primary == 'register'

    def test_multiple_fields_picks_dominant(self):
        """Multiple body fields outweigh single ornament field."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        shared = {
            'neckline': 'v-neck',
            'waistline': 'natural',
            'sleeve_length': 'long',
            'material': 'silk',
        }
        primary, secondary = _derive_axes_from_shared(shared)
        assert primary == 'body'  # 3 body fields vs 1 ornament
        assert secondary == 'ornament'

    def test_empty_shared_returns_none(self):
        """No shared attributes → both axes are None."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        primary, secondary = _derive_axes_from_shared({})
        assert primary is None
        assert secondary is None

    def test_construction_technique_splits(self):
        """construction_technique contributes to both volume and ornament."""
        from tools.analysis.classify_bridge_dimensions import _derive_axes_from_shared
        shared = {'construction_technique': ['hand-embroidery']}
        primary, secondary = _derive_axes_from_shared(shared)
        # Should contribute 0.5 to volume AND 0.5 to ornament
        assert primary in ('volume', 'ornament')
