"""Tests for the canonical era taxonomy module."""

import pytest
from enrichment.era_taxonomy import (
    ERAS, ERA_NAMES, PERIODS, ERAS_BY_PERIOD, ERA_ALIASES,
    ERA_NAME_LOWER, year_to_era, normalize_era, build_era_prompt_section,
)


class TestEraRegistry:
    """Test the canonical era registry structure."""

    def test_era_count(self):
        assert len(ERA_NAMES) >= 50

    def test_all_eras_have_required_fields(self):
        for name, data in ERAS.items():
            assert "start" in data, f"{name} missing start"
            assert "end" in data, f"{name} missing end"
            assert "period" in data, f"{name} missing period"
            assert "keywords" in data, f"{name} missing keywords"
            assert isinstance(data["keywords"], list), f"{name} keywords not a list"
            assert data["start"] < data["end"], f"{name} start >= end"

    def test_periods_ordered(self):
        expected = [
            "Ancient & Classical", "Medieval", "Renaissance & Early Modern",
            "17th Century", "18th Century", "19th Century",
            "Early 20th Century", "Mid 20th Century",
            "Late 20th Century", "21st Century",
        ]
        assert PERIODS == expected

    def test_eras_by_period_covers_all(self):
        all_from_periods = []
        for eras in ERAS_BY_PERIOD.values():
            all_from_periods.extend(eras)
        assert set(all_from_periods) == set(ERA_NAMES)

    def test_era_name_lower_complete(self):
        assert len(ERA_NAME_LOWER) == len(ERA_NAMES)
        for name in ERA_NAMES:
            assert name.lower() in ERA_NAME_LOWER


class TestYearToEra:
    """Test year-to-era mapping."""

    def test_ancient(self):
        assert year_to_era(-500) == "Ancient Greek"

    def test_medieval(self):
        assert year_to_era(1300) == "Gothic / High Medieval"

    def test_victorian_bustle(self):
        assert year_to_era(1875) == "Victorian Late / Bustle"

    def test_edwardian(self):
        assert year_to_era(1905) == "Edwardian"

    def test_roaring_twenties(self):
        assert year_to_era(1925) == "Roaring Twenties / Art Deco"

    def test_space_age(self):
        # 1962 is only in Space Age (1960-1969), not Hippie (1965-1974)
        assert year_to_era(1962) == "Space Age"

    def test_modern(self):
        result = year_to_era(2023)
        assert result is not None
        assert result in ERA_NAMES

    def test_out_of_range(self):
        assert year_to_era(-5000) is None

    def test_prefers_specific_era(self):
        """Overlapping ranges should return the more specific (shorter span) era."""
        # 1660 is in both Baroque (1625-1700) and Restoration (1660-1685)
        # Restoration is shorter, so should win
        assert year_to_era(1670) == "Restoration"

    def test_boundary_year(self):
        # 1800 is the start of Empire / Regency
        assert year_to_era(1800) == "Empire / Regency"


class TestNormalizeEra:
    """Test era normalization."""

    def test_exact_match(self):
        assert normalize_era("Quiet Luxury") == "Quiet Luxury"
        assert normalize_era("Baroque") == "Baroque"

    def test_case_insensitive(self):
        assert normalize_era("quiet luxury") == "Quiet Luxury"
        assert normalize_era("BAROQUE") == "Baroque"

    def test_alias_match(self):
        assert normalize_era("victorian") == "Victorian Late / Bustle"
        assert normalize_era("Jazz Age") == "Roaring Twenties / Art Deco"
        assert normalize_era("art deco") == "Roaring Twenties / Art Deco"

    def test_decade_alias(self):
        assert normalize_era("1920s") == "Roaring Twenties / Art Deco"
        assert normalize_era("1870s") == "Victorian Late / Bustle"
        assert normalize_era("1950s") == "Atomic Age"

    def test_legacy_loader_alias(self):
        assert normalize_era("pre-1700s") == "Baroque"
        assert normalize_era("colonial") == "Rococo"
        assert normalize_era("counterculture") == "Hippie / Counterculture"

    def test_suffix_stripping(self):
        assert normalize_era("Baroque era") == "Baroque"
        assert normalize_era("Rococo period") == "Rococo"

    def test_none_input(self):
        assert normalize_era(None) is None

    def test_empty_string(self):
        assert normalize_era("") is None

    def test_unknown_passthrough(self):
        assert normalize_era("Totally Made Up") == "Totally Made Up"

    def test_whitespace_handling(self):
        assert normalize_era("  Quiet Luxury  ") == "Quiet Luxury"


class TestAliasIntegrity:
    """Ensure every alias maps to a valid canonical era."""

    def test_all_aliases_resolve(self):
        for alias, canonical in ERA_ALIASES.items():
            assert canonical in ERA_NAMES, (
                f"Alias '{alias}' maps to '{canonical}' which is not a canonical era name"
            )


class TestBuildPromptSection:
    """Test prompt section generation."""

    def test_non_empty(self):
        prompt = build_era_prompt_section()
        assert len(prompt) > 100

    def test_contains_all_eras(self):
        prompt = build_era_prompt_section()
        for name in ERA_NAMES:
            assert name in prompt, f"Era '{name}' not found in prompt section"

    def test_contains_all_periods(self):
        prompt = build_era_prompt_section()
        for period in PERIODS:
            assert period in prompt, f"Period '{period}' not found in prompt section"
