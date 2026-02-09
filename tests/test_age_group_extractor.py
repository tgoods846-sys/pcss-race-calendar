"""Tests for age group extraction including keyword inference."""

import pytest
from ingestion.age_group_extractor import extract_age_groups


class TestExplicitUCodes:
    def test_single_u_code(self):
        assert extract_age_groups("U14 Qualifier", []) == ["U14"]

    def test_multiple_u_codes(self):
        assert extract_age_groups("U12/U14 Spring Fling", []) == ["U12", "U14"]

    def test_u_codes_in_categories(self):
        assert extract_age_groups("Some Race", ["U10/U12/U14"]) == ["U10", "U12", "U14"]

    def test_u_codes_in_both(self):
        assert extract_age_groups("U16 Qualifier", ["U14 U16"]) == ["U14", "U16"]

    def test_no_u_codes(self):
        assert extract_age_groups("South Series", []) == []


class TestKeywordInference:
    def test_devo_implies_u16_u18_u21(self):
        result = extract_age_groups("WR Devo FIS", [])
        assert result == ["U16", "U18", "U21"]

    def test_ysl_implies_u10_u12(self):
        result = extract_age_groups("YSL Finals", [])
        assert result == ["U10", "U12"]

    def test_imc_implies_u14_u16(self):
        result = extract_age_groups("IMC SnowCup", [])
        assert result == ["U14", "U16"]

    def test_njr_implies_u16_u18_u21(self):
        result = extract_age_groups("WR Devo / NJR", [])
        assert result == ["U16", "U18", "U21"]

    def test_nationals_implies_u16(self):
        result = extract_age_groups("USSS Nationals", [])
        assert result == ["U16"]

    def test_fis_in_categories(self):
        result = extract_age_groups("Some Race", ["FIS"])
        assert result == ["U16", "U18", "U21"]

    def test_explicit_u_code_overrides_keyword(self):
        """When explicit U-codes exist, keywords should NOT add more."""
        result = extract_age_groups("U14 Devo Camp", [])
        assert result == ["U14"]

    def test_no_keywords_no_codes(self):
        result = extract_age_groups("South Series", [])
        assert result == []
