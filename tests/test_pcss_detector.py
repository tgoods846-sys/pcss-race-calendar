"""Tests for PCSS auto-detection from race result PDFs.

Run: python3 -m pytest tests/test_pcss_detector.py -v
"""

import json
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from ingestion.pcss_detector import (
    _parse_venue,
    _parse_dates,
    _venues_match,
    _dates_overlap,
    _match_to_event,
    _load_cache,
    _save_cache,
)


# --- Venue Parsing ---

class TestParseVenue:
    def test_simple_venue(self):
        assert _parse_venue("Sean Nurse IMD Open @ Snowking, 2SL/2GS- Dec. 20-23, 2025") == "Snow King"

    def test_multi_word_venue(self):
        assert _parse_venue("South Series @ Bogus Basin, SL/GS- Jan. 10-12, 2026") == "Bogus Basin"

    def test_abbreviated_venue(self):
        assert _parse_venue("IMC SnowCup @ JHMR, 2SL/2GS- Feb. 1-4, 2026") == "JHMR"

    def test_venue_no_disciplines(self):
        assert _parse_venue("WR Devo FIS @ Sun Valley- Mar. 5-7, 2026") == "Sun Valley"

    def test_no_at_sign(self):
        assert _parse_venue("Some Event Without Venue") == ""

    def test_snowking_normalization(self):
        assert _parse_venue("Event @ SnowKing, SL- Jan. 5, 2026") == "Snow King"


# --- Date Parsing ---

class TestParseDates:
    def test_date_range(self):
        start, end = _parse_dates("Event @ Venue, SL- Dec. 20-23, 2025")
        assert start == date(2025, 12, 20)
        assert end == date(2025, 12, 23)

    def test_single_date(self):
        start, end = _parse_dates("Event @ Venue- Jan. 5, 2026")
        assert start == date(2026, 1, 5)
        assert end == date(2026, 1, 5)

    def test_month_without_period(self):
        start, end = _parse_dates("Event @ Venue- Mar 14-16, 2025")
        assert start == date(2025, 3, 14)
        assert end == date(2025, 3, 16)

    def test_no_date(self):
        start, end = _parse_dates("Some random text")
        assert start is None
        assert end is None


# --- Venue Matching ---

class TestVenuesMatch:
    def test_exact_match(self):
        assert _venues_match("Snowbird", "Snowbird")

    def test_case_insensitive(self):
        assert _venues_match("snowbird", "Snowbird")

    def test_substring_match(self):
        assert _venues_match("Park City", "Park City Mountain")

    def test_no_match(self):
        assert not _venues_match("Snowbird", "Bogus Basin")

    def test_normalized_match(self):
        assert _venues_match("Snowking", "Snow King")


# --- Date Overlap ---

class TestDatesOverlap:
    def test_overlapping(self):
        assert _dates_overlap(
            date(2025, 12, 20), date(2025, 12, 23),
            date(2025, 12, 21), date(2025, 12, 24),
        )

    def test_exact_same(self):
        assert _dates_overlap(
            date(2025, 12, 20), date(2025, 12, 23),
            date(2025, 12, 20), date(2025, 12, 23),
        )

    def test_no_overlap(self):
        assert not _dates_overlap(
            date(2025, 12, 20), date(2025, 12, 23),
            date(2026, 1, 10), date(2026, 1, 12),
        )

    def test_tolerance_one_day(self):
        # Results end Dec 23, event starts Dec 24 — should match with tolerance=1
        assert _dates_overlap(
            date(2025, 12, 20), date(2025, 12, 23),
            date(2025, 12, 24), date(2025, 12, 25),
        )

    def test_beyond_tolerance(self):
        # 3 days apart — should NOT match with default tolerance=1
        assert not _dates_overlap(
            date(2025, 12, 20), date(2025, 12, 21),
            date(2025, 12, 25), date(2025, 12, 26),
        )


# --- Event Matching ---

class TestMatchToEvent:
    def _make_event(self, eid, venue, start, end):
        return {
            "id": eid,
            "venue": venue,
            "dates": {"start": start, "end": end},
        }

    def test_match_found(self):
        events = [
            self._make_event("imd-100", "Snow King", "2025-12-20", "2025-12-23"),
            self._make_event("imd-200", "Snowbird", "2026-01-10", "2026-01-12"),
        ]
        group = {
            "venue": "Snow King",
            "date_start": date(2025, 12, 20),
            "date_end": date(2025, 12, 23),
        }
        assert _match_to_event(group, events) == "imd-100"

    def test_no_match(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2025-12-20", "2025-12-23"),
        ]
        group = {
            "venue": "Bogus Basin",
            "date_start": date(2025, 12, 20),
            "date_end": date(2025, 12, 23),
        }
        assert _match_to_event(group, events) is None

    def test_venue_match_date_mismatch(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-03-01", "2026-03-03"),
        ]
        group = {
            "venue": "Snowbird",
            "date_start": date(2025, 12, 20),
            "date_end": date(2025, 12, 23),
        }
        assert _match_to_event(group, events) is None

    def test_normalized_venue_match(self):
        events = [
            self._make_event("imd-100", "Snow King", "2025-12-20", "2025-12-23"),
        ]
        group = {
            "venue": "Snow King",  # Already normalized by _parse_venue
            "date_start": date(2025, 12, 20),
            "date_end": date(2025, 12, 23),
        }
        assert _match_to_event(group, events) == "imd-100"


# --- PCSS Pattern Matching ---

class TestPCSSPatterns:
    """Test that PCSS patterns correctly match in text."""

    def test_pcss_abbreviation(self):
        from ingestion.config import PCSS_PATTERNS
        text = "John Smith  PCSS  1:23.45"
        assert any(p.search(text) for p in PCSS_PATTERNS)

    def test_park_city(self):
        from ingestion.config import PCSS_PATTERNS
        text = "Jane Doe  Park City  1:24.00"
        assert any(p.search(text) for p in PCSS_PATTERNS)

    def test_no_match(self):
        from ingestion.config import PCSS_PATTERNS
        text = "John Smith  Bogus Basin Ski Club  1:23.45"
        assert not any(p.search(text) for p in PCSS_PATTERNS)


# --- Cache ---

class TestCache:
    def test_load_missing_cache(self, tmp_path):
        from ingestion.config import PCSS_RESULTS_CACHE_PATH
        with patch("ingestion.pcss_detector.PCSS_RESULTS_CACHE_PATH", tmp_path / "missing.json"):
            cache = _load_cache()
            assert cache == {"last_checked": None, "checked_pdfs": {}}

    def test_save_and_load_cache(self, tmp_path):
        cache_path = tmp_path / "cache.json"
        with patch("ingestion.pcss_detector.PCSS_RESULTS_CACHE_PATH", cache_path):
            cache = {"last_checked": None, "checked_pdfs": {
                "http://example.com/test.pdf": {
                    "pcss_found": True,
                    "checked_at": "2026-01-01T00:00:00",
                }
            }}
            _save_cache(cache)

            loaded = _load_cache()
            assert loaded["checked_pdfs"]["http://example.com/test.pdf"]["pcss_found"] is True
            assert loaded["last_checked"] is not None
