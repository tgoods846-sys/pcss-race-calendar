"""Tests for racer name extraction from race result PDFs.

Run: python3 -m pytest tests/test_name_extractor.py -v
"""

import json
from unittest.mock import patch

import pytest

from ingestion.name_extractor import (
    parse_names_from_text,
    _normalize_name,
    _is_valid_name,
)


# --- Name Parsing from Text ---

class TestParseNamesFromText:
    def test_imd_format_basic(self):
        text = "  1  I6989553 Johnson, Feren 2010 PCSS USA 45.02 (2) 46.64 (5) 1:31.66\n  2  N6445585 Dain, Augustus 2006 MSU USA 45.95 (4) 45.99 (3) 1:31.94\n"
        names = parse_names_from_text(text)
        assert ("Feren Johnson", "feren johnson", "PCSS") in names
        assert ("Augustus Dain", "augustus dain", "MSU") in names

    def test_two_digit_bib(self):
        text = " 42  I6840472 Eaton, Brody 2011 RM USA 44.62\n"
        names = parse_names_from_text(text)
        assert ("Brody Eaton", "brody eaton", "RM") in names

    def test_three_digit_bib(self):
        text = "123  I6824065 Kinsman, Asher 2010 RM USA 46.59\n"
        names = parse_names_from_text(text)
        assert ("Asher Kinsman", "asher kinsman", "RM") in names

    def test_filters_header_words(self):
        text = "  1  I6989553 Results, Final 2010 USA\n  2  I6445585 Smith, John 2010 PCSS USA\n"
        names = parse_names_from_text(text)
        keys = [k for _, k, _ in names]
        assert "john smith" in keys
        assert not any("results" in k for k in keys)

    def test_deduplicates(self):
        text = "  1  I6989553 Smith, John 2010 PCSS USA 45.02\n  1  I6989553 Smith, John 2010 PCSS USA 44.00\n"
        names = parse_names_from_text(text)
        assert len(names) == 1
        assert ("John Smith", "john smith", "PCSS") in names

    def test_empty_text(self):
        assert parse_names_from_text("") == []

    def test_no_names_in_text(self):
        text = "This is just a paragraph with no race results.\n"
        assert parse_names_from_text(text) == []

    def test_hyphenated_name(self):
        text = "  5  I6801593 O'Brien, Mary-Kate 2010 SVST USA 45.75\n"
        names = parse_names_from_text(text)
        assert len(names) == 1
        display, key, club = names[0]
        assert display == "Mary-Kate O'Brien"
        assert key == "mary-kate o'brien"
        assert club == "SVST"

    def test_multiple_racers(self):
        text = (
            "  1  I6989553 Johnson, Feren 2010 PCSS USA 45.02\n"
            "  2  N6445585 Dain, Augustus 2006 MSU USA 45.95\n"
            "  3  I6840472 Eaton, Brody 2011 RM USA 44.62\n"
            "  4  I6824065 Kinsman, Asher 2010 RM USA 46.59\n"
        )
        names = parse_names_from_text(text)
        assert len(names) == 4

    def test_real_pdf_snippet(self):
        """Test against actual text extracted from an IMD result PDF."""
        text = (
            "Rank  Bib NAT Code Name   YB Club NAT       Run 1       Run 2       Total     Diff.   Points\n"
            "1  4 I6989553 Johnson, Feren 2010 PCSS USA 45.02 (2) 46.64 (5) 1:31.66     0.00\n"
            "2  3 N6445585 Dain, Augustus 2006 MSU USA 45.95 (4) 45.99 (3) 1:31.94 0.28     2.23\n"
            "3  5 I6840472 Eaton, Brody 2011 RM USA 44.62 (1) 47.33 (9) 1:31.95 0.29     2.31\n"
        )
        names = parse_names_from_text(text)
        assert len(names) == 3
        assert ("Feren Johnson", "feren johnson", "PCSS") in names
        assert ("Augustus Dain", "augustus dain", "MSU") in names
        assert ("Brody Eaton", "brody eaton", "RM") in names

    def test_club_codes_variety(self):
        """Multiple different club codes are extracted correctly."""
        text = (
            "  1  I6989553 Alpha, Anne 2010 PCSS USA 45.02\n"
            "  2  N6445585 Bravo, Bob 2009 SVSEF USA 45.95\n"
            "  3  I6840472 Charlie, Cara 2011 SVST USA 44.62\n"
            "  4  I6824065 Delta, Dan 2010 SB USA 46.59\n"
            "  5  I6824066 Echo, Eve 2008 MBSEF USA 47.00\n"
        )
        names = parse_names_from_text(text)
        clubs = {club for _, _, club in names}
        assert clubs == {"PCSS", "SVSEF", "SVST", "SB", "MBSEF"}

    def test_no_club(self):
        """Lines without a birth year + club return club=None via fallback."""
        text = "  1  I6989553 Smith, John\n"
        names = parse_names_from_text(text)
        assert len(names) == 1
        assert names[0] == ("John Smith", "john smith", None)

    def test_country_only_no_club(self):
        """When only a country code follows birth year (no club), club is None."""
        text = "  1  I6989553 Smith, John 2010 USA 45.02\n"
        names = parse_names_from_text(text)
        assert len(names) == 1
        _, _, club = names[0]
        assert club is None


# --- Name Normalization ---

class TestNormalizeName:
    def test_basic(self):
        assert _normalize_name("Smith", "John") == "John Smith"

    def test_title_case(self):
        assert _normalize_name("JONES", "SARAH") == "Sarah Jones"

    def test_hyphenated_last(self):
        result = _normalize_name("Smith-Jones", "Mary")
        assert result == "Mary Smith-Jones"

    def test_apostrophe_last(self):
        result = _normalize_name("O'Brien", "Pat")
        assert result == "Pat O'Brien"

    def test_hyphenated_first(self):
        result = _normalize_name("Smith", "Mary-Kate")
        assert result == "Mary-Kate Smith"


# --- Name Validation ---

class TestIsValidName:
    def test_valid_name(self):
        assert _is_valid_name("Smith", "John")

    def test_valid_hyphenated(self):
        assert _is_valid_name("O'Brien", "Mary")

    def test_header_word_official(self):
        assert not _is_valid_name("Official", "Results")

    def test_header_word_results(self):
        assert not _is_valid_name("Results", "Final")

    def test_header_word_slalom(self):
        assert not _is_valid_name("Slalom", "Giant")

    def test_header_word_dnf(self):
        assert not _is_valid_name("DNF", "Smith")

    def test_too_short_last(self):
        assert not _is_valid_name("S", "John")

    def test_too_short_first(self):
        assert not _is_valid_name("Smith", "J")

    def test_digit_last(self):
        assert not _is_valid_name("123", "John")

    def test_digit_first(self):
        assert not _is_valid_name("Smith", "123")

    def test_header_word_rank(self):
        assert not _is_valid_name("Rank", "Name")

    def test_header_word_team(self):
        assert not _is_valid_name("Team", "Club")
