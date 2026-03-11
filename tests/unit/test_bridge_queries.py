"""
Unit tests for bridge query helpers.

Tests internal conversion functions and canonical ordering logic
without requiring database or Qdrant connections.
"""
import json
import pytest
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from analysis.bridge_queries import (
    _parse_json_field,
    _product_to_summary,
    _build_bridge_result,
)


# ---------------------------------------------------------------------------
# Mock objects
# ---------------------------------------------------------------------------

class MockProduct:
    """Minimal mock matching Product model attributes."""
    def __init__(self, **kwargs):
        defaults = {
            'id': 1, 'platform': 'met_museum', 'title': 'Test Dress',
            'primary_image': None, 'era': 'Victorian', 'decade': '1870s',
            'fp_category': 'dress', 'silhouette': 'a-line', 'vibe': 'romantic',
            'material': 'silk', 'style_tags': '["elegant", "formal"]',
            'colors': '["red", "gold"]', 'ai_description': 'A beautiful dress.',
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


class MockBridge:
    """Minimal mock matching StyleBridge model attributes."""
    def __init__(self, **kwargs):
        defaults = {
            'id': 100, 'source_id': 1, 'target_id': 2,
            'text_similarity': 0.90,
            'image_similarity': 0.70, 'structural_score': 0.80,
            'connection_mode': None,
            'bridge_type': 'same_era', 'bridge_narrative': 'They share DNA.',
            'shared_attributes': '{"fp_category": "dress", "silhouette": "a-line"}',
            'created_at': datetime(2026, 2, 20, 12, 0, 0),
            'temporal_type': None,
            'crossing_type': None,
            'primary_axis': None,
            'secondary_axis': None,
            'contrast_pair': None,
        }
        defaults.update(kwargs)
        for k, v in defaults.items():
            setattr(self, k, v)


# ---------------------------------------------------------------------------
# _parse_json_field
# ---------------------------------------------------------------------------

class TestParseJsonField:
    def test_valid_json_array(self):
        assert _parse_json_field('["a", "b", "c"]') == ["a", "b", "c"]

    def test_none_returns_empty(self):
        assert _parse_json_field(None) == []

    def test_empty_string_returns_empty(self):
        assert _parse_json_field('') == []

    def test_malformed_json_returns_empty(self):
        assert _parse_json_field('not json') == []

    def test_json_object_returns_empty(self):
        """Non-list JSON should return empty list."""
        assert _parse_json_field('{"key": "val"}') == []

    def test_nested_arrays(self):
        result = _parse_json_field('[["a", "b"], ["c"]]')
        assert result == [["a", "b"], ["c"]]


# ---------------------------------------------------------------------------
# _product_to_summary
# ---------------------------------------------------------------------------

class TestProductToSummary:
    def test_basic_conversion(self):
        p = MockProduct()
        s = _product_to_summary(p)
        assert s['id'] == 1
        assert s['platform'] == 'met_museum'
        assert s['title'] == 'Test Dress'
        assert s['era'] == 'Victorian'
        assert s['fp_category'] == 'dress'

    def test_json_fields_parsed(self):
        p = MockProduct(
            style_tags='["glamorous", "evening"]',
            colors='["black", "silver"]',
        )
        s = _product_to_summary(p)
        assert s['style_tags'] == ['glamorous', 'evening']
        assert s['colors'] == ['black', 'silver']

    def test_none_json_fields(self):
        p = MockProduct(style_tags=None, colors=None)
        s = _product_to_summary(p)
        assert s['style_tags'] == []
        assert s['colors'] == []

    def test_none_title_becomes_empty_string(self):
        p = MockProduct(title=None)
        s = _product_to_summary(p)
        assert s['title'] == ''

    def test_all_optional_fields_can_be_none(self):
        p = MockProduct(
            era=None, decade=None, fp_category=None,
            silhouette=None, vibe=None, material=None,
            ai_description=None, primary_image=None,
        )
        s = _product_to_summary(p)
        assert s['era'] is None
        assert s['decade'] is None
        assert s['material'] is None


# ---------------------------------------------------------------------------
# _build_bridge_result
# ---------------------------------------------------------------------------

class TestBuildBridgeResult:
    def setup_method(self):
        p1 = MockProduct(id=1, title='Dress A')
        p2 = MockProduct(id=2, title='Dress B')
        self.product_map = {
            1: _product_to_summary(p1),
            2: _product_to_summary(p2),
        }

    def test_basic_assembly(self):
        b = MockBridge()
        result = _build_bridge_result(b, self.product_map)
        assert result is not None
        assert result['id'] == 100
        # Computed: 0.40*0.90 + 0.30*0.70 + 0.30*0.80 = 0.81
        assert result['bridge_score'] == 0.81
        assert result['source']['title'] == 'Dress A'
        assert result['target']['title'] == 'Dress B'

    def test_shared_attributes_parsed(self):
        b = MockBridge(shared_attributes='{"fp_category": "dress"}')
        result = _build_bridge_result(b, self.product_map)
        assert result['shared_attributes'] == {'fp_category': 'dress'}

    def test_null_shared_attributes(self):
        b = MockBridge(shared_attributes=None)
        result = _build_bridge_result(b, self.product_map)
        assert result['shared_attributes'] == {}

    def test_malformed_shared_attributes(self):
        b = MockBridge(shared_attributes='not json')
        result = _build_bridge_result(b, self.product_map)
        assert result['shared_attributes'] == {}

    def test_missing_source_returns_none(self):
        b = MockBridge(source_id=999)
        result = _build_bridge_result(b, self.product_map)
        assert result is None

    def test_missing_target_returns_none(self):
        b = MockBridge(target_id=999)
        result = _build_bridge_result(b, self.product_map)
        assert result is None

    def test_created_at_is_iso_string(self):
        b = MockBridge(created_at=datetime(2026, 2, 20, 14, 30, 0))
        result = _build_bridge_result(b, self.product_map)
        assert result['created_at'] == '2026-02-20T14:30:00'

    def test_null_created_at(self):
        b = MockBridge(created_at=None)
        result = _build_bridge_result(b, self.product_map)
        assert result['created_at'] == ''

    def test_null_image_similarity(self):
        b = MockBridge(image_similarity=None)
        result = _build_bridge_result(b, self.product_map)
        assert result['image_similarity'] is None

    def test_bridge_type_and_narrative(self):
        b = MockBridge(bridge_type='transmission', bridge_narrative='A nice story.')
        result = _build_bridge_result(b, self.product_map)
        assert result['bridge_type'] == 'transmission'
        assert result['bridge_narrative'] == 'A nice story.'
