"""
Unit tests for bridge computation logic.

Tests structural scoring, temporal classification, and date extraction
without requiring database or Qdrant connections.
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analysis.compute_bridges import (
    compute_structural_score,
    classify_temporal_type,
    extract_approximate_year,
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
            'era': None, 'vibe': None,
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
        assert score > 0.8
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
# Temporal classification
# ---------------------------------------------------------------------------

class TestTemporalClassification:
    """classify_temporal_type correctness."""

    def test_cross_era_by_date(self):
        result = classify_temporal_type('met_museum', 'fashionpedia', 1860, 2020)
        assert result == 'cross_era'

    def test_near_era_by_date(self):
        result = classify_temporal_type('met_museum', 'met_museum', 1900, 1920)
        assert result == 'near_era'

    def test_same_era_by_date(self):
        result = classify_temporal_type('met_museum', 'met_museum', 1860, 1865)
        assert result == 'same_era'

    def test_platform_fallback_cross_era(self):
        """Historical vs modern platform → cross_era when no dates."""
        result = classify_temporal_type('met_museum', 'fashionpedia', None, None)
        assert result == 'cross_era'

    def test_platform_fallback_same_era(self):
        """Same platform type → same_era when no dates."""
        result = classify_temporal_type('met_museum', 'smithsonian', None, None)
        assert result == 'same_era'

    def test_boundary_cross_era(self):
        """Exactly 31 years apart → cross_era."""
        result = classify_temporal_type('a', 'b', 1900, 1931)
        assert result == 'cross_era'

    def test_boundary_near_era(self):
        """Exactly 11 years apart → near_era."""
        result = classify_temporal_type('a', 'b', 1900, 1911)
        assert result == 'near_era'

    def test_boundary_same_era(self):
        """Exactly 10 years apart → same_era."""
        result = classify_temporal_type('a', 'b', 1900, 1910)
        assert result == 'same_era'


# ---------------------------------------------------------------------------
# Date extraction
# ---------------------------------------------------------------------------

class TestDateExtraction:
    """extract_approximate_year correctness."""

    def test_direct_year(self):
        p = MockProduct(year=1865)
        assert extract_approximate_year(p) == 1865

    def test_decade_parsing(self):
        p = MockProduct(decade='1870s')
        assert extract_approximate_year(p) == 1875

    def test_object_date_range(self):
        p = MockProduct(object_date='1860-1870')
        assert extract_approximate_year(p) == 1865

    def test_object_date_circa(self):
        p = MockProduct(object_date='ca. 1920')
        assert extract_approximate_year(p) == 1920

    def test_object_date_bare_year(self):
        p = MockProduct(object_date='1955')
        assert extract_approximate_year(p) == 1955

    def test_object_date_century(self):
        p = MockProduct(object_date='late 19th century')
        assert extract_approximate_year(p) == 1880

    def test_era_fallback(self):
        p = MockProduct(era='Victorian')
        assert extract_approximate_year(p) == 1870

    def test_no_date_returns_none(self):
        p = MockProduct()
        assert extract_approximate_year(p) is None

    def test_priority_year_over_decade(self):
        """Direct year takes priority over decade."""
        p = MockProduct(year=1920, decade='1930s')
        assert extract_approximate_year(p) == 1920
