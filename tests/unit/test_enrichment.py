"""
Unit tests for enrichment/claude.py

Tests build_rich_text(), _get_fallback_enrichment(), _build_enrichment_prompt(),
and JSON parsing logic. Claude API calls are mocked.
"""
import pytest
import json
from unittest.mock import patch, MagicMock


def _make_enricher():
    """Create a ClaudeEnricher with mocked API key and client."""
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
        with patch("anthropic.Anthropic"):
            from enrichment.claude import ClaudeEnricher
            return ClaudeEnricher()


# ---- build_rich_text tests ----


class TestBuildRichText:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.enricher = _make_enricher()

    def test_full_enrichment_produces_nonempty_text(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert isinstance(text, str)
        assert len(text) > 50

    def test_ai_description_appears_first(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert text.startswith(sample_enrichment["ai_description"])

    def test_era_and_decade_included(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "Art Deco" in text
        assert "1920s" in text

    def test_silhouette_in_output(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "a-line silhouette" in text

    def test_style_tags_in_output(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        for tag in sample_enrichment["style_tags"]:
            assert tag in text

    def test_decorations_in_output(self, sample_product_data, sample_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "Details:" in text
        assert "sequin" in text

    def test_plain_pattern_excluded(self, sample_product_data, sample_enrichment):
        """textile_pattern='plain' should NOT appear as 'plain pattern'."""
        sample_enrichment["textile_pattern"] = "plain"
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "plain pattern" not in text

    def test_nonplain_pattern_included(self, sample_product_data, sample_enrichment):
        sample_enrichment["textile_pattern"] = "floral"
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "floral pattern" in text

    def test_minimal_enrichment_still_works(self, sample_product_data, minimal_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, minimal_enrichment)
        assert isinstance(text, str)
        assert len(text) > 10

    def test_empty_decorations_no_details_section(self, sample_product_data, minimal_enrichment):
        text = self.enricher.build_rich_text(sample_product_data, minimal_enrichment)
        assert "Details:" not in text

    def test_colors_limited_to_three(self, sample_product_data, sample_enrichment):
        sample_enrichment["colors"] = ["red", "blue", "green", "yellow", "purple"]
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "yellow" not in text
        assert "red" in text

    def test_only_first_two_finishing_techniques(self, sample_product_data, sample_enrichment):
        sample_enrichment["textile_finishing"] = ["pleated", "ruched", "cutout", "slit"]
        text = self.enricher.build_rich_text(sample_product_data, sample_enrichment)
        assert "pleated" in text
        assert "ruched" in text
        assert "cutout" not in text


# ---- _get_fallback_enrichment tests ----


class TestFallbackEnrichment:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.enricher = _make_enricher()

    def test_returns_all_23_fields(self):
        result = self.enricher._get_fallback_enrichment("Test Title", "Shirts")
        expected_keys = {
            "fp_category", "nickname", "silhouette", "neckline", "waistline",
            "length", "sleeve_length", "opening_type", "textile_pattern",
            "textile_finishing", "garment_parts", "decorations",
            "era", "decade", "style_tags", "colors", "material",
            "season", "garment_type", "vibe", "fit_style", "occasion",
            "ai_description",
        }
        assert set(result.keys()) == expected_keys

    def test_garment_type_is_lowercased_category(self):
        result = self.enricher._get_fallback_enrichment("Some Title", "Shirts")
        assert result["garment_type"] == "shirts"

    def test_title_in_ai_description(self):
        result = self.enricher._get_fallback_enrichment("Navy Blue Shirt", "Shirts")
        assert "Navy Blue Shirt" in result["ai_description"]

    def test_defaults_are_safe(self):
        result = self.enricher._get_fallback_enrichment("X", "Y")
        assert result["textile_pattern"] == "plain"
        assert result["textile_finishing"] == []
        assert result["garment_parts"] == []
        assert result["decorations"] == []
        assert result["era"] == "Modern"

    @pytest.mark.parametrize("category", ["Dress", "JACKET", "pants", "Skirt"])
    def test_category_variations(self, category):
        result = self.enricher._get_fallback_enrichment("T", category)
        assert result["garment_type"] == category.lower()


# ---- _build_enrichment_prompt tests ----


class TestBuildEnrichmentPrompt:

    @pytest.fixture(autouse=True)
    def _setup(self):
        self.enricher = _make_enricher()

    def test_title_and_category_in_prompt(self):
        prompt = self.enricher._build_enrichment_prompt(
            "Silk Gown", "dress", None, None, None
        )
        assert "Silk Gown" in prompt
        assert "dress" in prompt

    def test_optional_fields_included_when_present(self):
        prompt = self.enricher._build_enrichment_prompt(
            "Gown", "dress", "blue", None, None,
            material="silk", era="Victorian", culture="French",
            object_date="ca. 1870"
        )
        assert "blue" in prompt
        assert "Victorian" in prompt
        assert "French" in prompt
        assert "silk" in prompt
        assert "ca. 1870" in prompt

    def test_optional_fields_absent_when_none(self):
        prompt = self.enricher._build_enrichment_prompt(
            "Gown", "dress", None, None, None
        )
        assert "- Era:" not in prompt
        assert "- Culture:" not in prompt

    def test_prompt_requests_json_output(self):
        prompt = self.enricher._build_enrichment_prompt(
            "Gown", "dress", None, None, None
        )
        assert "JSON" in prompt
        assert "fp_category" in prompt

    def test_year_formatted_as_int(self):
        prompt = self.enricher._build_enrichment_prompt(
            "Shirt", "tops", None, None, 2011.0
        )
        assert "2011" in prompt
        assert "2011.0" not in prompt


# ---- JSON parsing logic (via enrich_product with mocked API) ----


class TestJSONParsing:

    @pytest.fixture(autouse=True)
    def _setup(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "fake-key"}):
            with patch("anthropic.Anthropic") as mock_anthropic:
                from enrichment.claude import ClaudeEnricher
                self.enricher = ClaudeEnricher()
                self.mock_client = mock_anthropic.return_value
                self.enricher.client = self.mock_client

    def _mock_response(self, text):
        mock_resp = MagicMock()
        mock_resp.content = [MagicMock(text=text)]
        self.mock_client.messages.create.return_value = mock_resp

    def test_clean_json_parsed(self, mock_claude_response_clean):
        self._mock_response(mock_claude_response_clean)
        result = self.enricher.enrich_product("Gown", "dress")
        assert result["fp_category"] == "dress"
        assert result["era"] == "Victorian"

    def test_markdown_wrapped_json_parsed(self, mock_claude_response_markdown_wrapped):
        self._mock_response(mock_claude_response_markdown_wrapped)
        result = self.enricher.enrich_product("Gown", "dress")
        assert result["fp_category"] == "dress"

    def test_generic_fence_json_parsed(self, mock_claude_response_generic_fence):
        self._mock_response(mock_claude_response_generic_fence)
        result = self.enricher.enrich_product("Gown", "dress")
        assert result["fp_category"] == "dress"

    def test_malformed_json_returns_fallback(self, mock_claude_response_malformed):
        self._mock_response(mock_claude_response_malformed)
        result = self.enricher.enrich_product("Gown", "dress")
        assert result["era"] == "Modern"
        assert result["fp_category"] is None
