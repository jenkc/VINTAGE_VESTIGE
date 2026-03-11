"""
Unit tests for bridge computation logic.

Tests structural scoring, temporal classification (named-era),
and revival threshold without requiring database or Qdrant connections.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tools.analysis.compute_bridges import (
    compute_structural_score,
    classify_temporal_type,
    parse_decade_to_year,
    CONTINUATION_DISTANCE,
)


# ---------------------------------------------------------------------------
# Mock product for testing
# ---------------------------------------------------------------------------

class MockProduct:
    """Minimal mock matching Product model attributes."""
    def __init__(self, **kwargs):
        defaults = {
            'id': 1, 'platform': 'met_museum', 'title': 'Test',
            'fp_category': None, 'silhouette': None, 'nickname': None,
            'neckline': None, 'length': None, 'waistline': None,
            'sleeve_length': None, 'textile_pattern': None,
            'opening_type': None, 'garment_parts': None,
            'decorations': None, 'textile_finishing': None,
            'year': None, 'decade': None, 'object_date': None,
            'era': None, 'vibe': None, 'culture': None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# Structural scoring
# ---------------------------------------------------------------------------

class TestStructuralScore:
    """compute_structural_score correctness."""

    def test_identical_products_score_high(self):
        a = MockProduct(
            fp_category='dress', silhouette='a-line', nickname='gown',
            neckline='v-neck', length='floor length', waistline='empire waistline',
            sleeve_length='sleeveless', textile_pattern='floral',
        )
        b = MockProduct(
            fp_category='dress', silhouette='a-line', nickname='gown',
            neckline='v-neck', length='floor length', waistline='empire waistline',
            sleeve_length='sleeveless', textile_pattern='floral',
        )
        score, shared = compute_structural_score(a, b)
        assert score > 0.5  # 8/15 weighted fields match
        assert 'fp_category' in shared
        assert shared['fp_category'] == 'dress'

    def test_completely_different_products_score_zero(self):
        a = MockProduct(fp_category='dress', silhouette='a-line')
        b = MockProduct(fp_category='jacket', silhouette='straight')
        score, shared = compute_structural_score(a, b)
        assert score == 0.0
        assert len(shared) == 0

    def test_partial_match_scores_between_zero_and_one(self):
        a = MockProduct(fp_category='dress', silhouette='a-line', neckline='v-neck')
        b = MockProduct(fp_category='dress', silhouette='fit and flare', neckline='v-neck')
        score, shared = compute_structural_score(a, b)
        assert 0.0 < score < 1.0
        assert 'fp_category' in shared
        assert 'neckline' in shared
        assert 'silhouette' not in shared

    def test_none_fields_dont_match(self):
        a = MockProduct(fp_category=None, silhouette=None)
        b = MockProduct(fp_category=None, silhouette=None)
        score, shared = compute_structural_score(a, b)
        assert score == 0.0

    def test_set_fields_use_jaccard(self):
        """garment_parts, decorations, textile_finishing use Jaccard similarity."""
        a = MockProduct(garment_parts='["collar", "sleeve", "pocket"]')
        b = MockProduct(garment_parts='["collar", "sleeve"]')
        score, shared = compute_structural_score(a, b)
        assert score > 0.0
        assert 'garment_parts' in shared
        assert 'collar' in shared['garment_parts']
        assert 'sleeve' in shared['garment_parts']

    def test_case_insensitive_matching(self):
        a = MockProduct(fp_category='Dress', silhouette='A-Line')
        b = MockProduct(fp_category='dress', silhouette='a-line')
        score, shared = compute_structural_score(a, b)
        assert score > 0.0


# ---------------------------------------------------------------------------
# Temporal classification (named-era)
# ---------------------------------------------------------------------------

class TestTemporalClassification:
    """classify_temporal_type uses named eras with platform fallback."""

    def test_different_eras_returns_transmission(self):
        result = classify_temporal_type('Victorian', 'Contemporary', 'met_museum', 'fashionpedia')
        assert result == 'transmission'

    def test_same_era_no_decades_returns_contemporary(self):
        result = classify_temporal_type('Art Deco', 'Art Deco', 'met_museum', 'smithsonian')
        assert result == 'contemporary'

    def test_same_era_close_decades_returns_contemporary(self):
        result = classify_temporal_type(
            'Victorian', 'Victorian', 'met_museum', 'smithsonian',
            '1860s', '1870s',
        )
        assert result == 'contemporary'

    def test_same_era_far_decades_returns_continuation(self):
        result = classify_temporal_type(
            'Victorian', 'Victorian', 'met_museum', 'smithsonian',
            '1840s', '1890s',
        )
        assert result == 'continuation'

    def test_case_insensitive(self):
        result = classify_temporal_type('victorian', 'VICTORIAN', 'met_museum', 'smithsonian')
        assert result == 'contemporary'

    def test_whitespace_stripped(self):
        result = classify_temporal_type('  Art Deco ', 'Art Deco', 'met_museum', 'smithsonian')
        assert result == 'contemporary'

    def test_platform_fallback_historical_vs_modern(self):
        """Historical vs modern platform → transmission when no eras."""
        result = classify_temporal_type(None, None, 'met_museum', 'fashionpedia')
        assert result == 'transmission'

    def test_platform_fallback_modern_vs_historical(self):
        """Reversed direction: modern vs historical → transmission."""
        result = classify_temporal_type(None, None, 'fashionpedia', 'smithsonian')
        assert result == 'transmission'

    def test_platform_fallback_same_type_returns_none(self):
        """Same platform type with no eras/decades → None (unknown)."""
        result = classify_temporal_type(None, None, 'met_museum', 'smithsonian')
        assert result is None

    def test_one_era_missing_uses_platform_fallback(self):
        """If only one product has an era, fall back to platform."""
        result = classify_temporal_type('Victorian', None, 'met_museum', 'fashionpedia')
        assert result == 'transmission'


# ---------------------------------------------------------------------------
# Revival classification
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Decade parsing
# ---------------------------------------------------------------------------

class TestDecadeParsing:
    """parse_decade_to_year correctness."""

    def test_standard_decade(self):
        assert parse_decade_to_year('1870s') == 1875

    def test_modern_decade(self):
        assert parse_decade_to_year('2020s') == 2025

    def test_none_returns_none(self):
        assert parse_decade_to_year(None) is None

    def test_empty_string_returns_none(self):
        assert parse_decade_to_year('') is None

    def test_whitespace_stripped(self):
        assert parse_decade_to_year('  1920s  ') == 1925

    def test_invalid_returns_none(self):
        assert parse_decade_to_year('unknown') is None


# ---------------------------------------------------------------------------
# Cross-time classification
# ---------------------------------------------------------------------------

class TestContinuationClassification:
    """continuation: same era, decades 20+ years apart."""

    def test_distance_constant(self):
        assert CONTINUATION_DISTANCE == 20

    def test_exactly_20_years_returns_continuation(self):
        """20 years is >= 20, should be continuation."""
        result = classify_temporal_type(
            'Victorian', 'Victorian', 'met_museum', 'smithsonian',
            '1850s', '1870s',  # 1855 vs 1875 = 20
        )
        assert result == 'continuation'

    def test_under_20_years_returns_contemporary(self):
        """Under 20 years → contemporary."""
        result = classify_temporal_type(
            'Victorian', 'Victorian', 'met_museum', 'smithsonian',
            '1860s', '1870s',  # 1865 vs 1875 = 10
        )
        assert result == 'contemporary'

    def test_different_eras_still_transmission(self):
        """transmission takes precedence regardless of decade distance."""
        result = classify_temporal_type(
            'Victorian', 'Art Deco', 'met_museum', 'smithsonian',
            '1870s', '1920s',
        )
        assert result == 'transmission'
