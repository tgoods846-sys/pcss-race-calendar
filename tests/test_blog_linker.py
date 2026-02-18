"""Tests for blog recap auto-linker.

Run: python3 -m pytest tests/test_blog_linker.py -v
"""

import json
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from ingestion.blog_linker import (
    _build_venue_slug_map,
    _extract_venue_from_slug,
    _fetch_rss_items,
    _match_blog_to_event,
    discover_blog_links,
)


# --- Venue Slug Map ---

class TestBuildVenueSlugMap:
    def test_single_word_venue(self):
        slug_map = _build_venue_slug_map()
        assert slug_map["snowbird"] == "Snowbird"

    def test_multi_word_venue(self):
        slug_map = _build_venue_slug_map()
        assert slug_map["sun-valley"] == "Sun Valley"

    def test_aliases_present(self):
        slug_map = _build_venue_slug_map()
        assert slug_map["uop"] == "Utah Olympic Park"
        assert slug_map["jhmr"] == "Jackson Hole"

    def test_dot_venue(self):
        slug_map = _build_venue_slug_map()
        assert slug_map["mt-bachelor"] == "Mt. Bachelor"

    def test_utah_olympic_park_auto(self):
        slug_map = _build_venue_slug_map()
        assert slug_map["utah-olympic-park"] == "Utah Olympic Park"


# --- Venue Extraction from Slug ---

class TestExtractVenueFromSlug:
    def setup_method(self):
        self.slug_map = _build_venue_slug_map()

    def test_snowbird(self):
        venue = _extract_venue_from_slug(
            "hartlauer-memorial-south-series-gs-at-snowbird", self.slug_map
        )
        assert venue == "Snowbird"

    def test_uop_alias(self):
        venue = _extract_venue_from_slug(
            "nolan-morris-takes-3rd-at-ysl-kombi-uop", self.slug_map
        )
        assert venue == "Utah Olympic Park"

    def test_sun_valley(self):
        venue = _extract_venue_from_slug(
            "race-recap-sun-valley-gs", self.slug_map
        )
        assert venue == "Sun Valley"

    def test_no_venue(self):
        venue = _extract_venue_from_slug(
            "general-skiing-news-update", self.slug_map
        )
        assert venue is None

    def test_longest_match(self):
        """'utah-olympic-park' should match before 'park' (from Park City)."""
        venue = _extract_venue_from_slug(
            "race-at-utah-olympic-park-results", self.slug_map
        )
        assert venue == "Utah Olympic Park"

    def test_empty_slug(self):
        assert _extract_venue_from_slug("", self.slug_map) is None

    def test_none_slug(self):
        assert _extract_venue_from_slug(None, self.slug_map) is None


# --- Event Matching ---

class TestMatchBlogToEvent:
    def setup_method(self):
        self.slug_map = _build_venue_slug_map()

    def _make_event(self, eid, venue, start, end, status="completed"):
        return {
            "id": eid,
            "venue": venue,
            "dates": {"start": start, "end": end},
            "status": status,
        }

    def test_venue_and_date_match(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-02-08", "2026-02-09"),
        ]
        item = {
            "title": "GS at Snowbird",
            "link": "https://example.com/post/gs-at-snowbird",
            "slug": "gs-at-snowbird",
            "pub_date": date(2026, 2, 10),
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid == "imd-100"
        assert venue == "Snowbird"

    def test_wrong_venue(self):
        events = [
            self._make_event("imd-100", "Bogus Basin", "2026-02-08", "2026-02-09"),
        ]
        item = {
            "title": "GS at Snowbird",
            "link": "https://example.com/post/gs-at-snowbird",
            "slug": "gs-at-snowbird",
            "pub_date": date(2026, 2, 10),
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid is None

    def test_outside_lookback_window(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-01-01", "2026-01-02"),
        ]
        item = {
            "title": "GS at Snowbird",
            "link": "https://example.com/post/gs-at-snowbird",
            "slug": "gs-at-snowbird",
            "pub_date": date(2026, 2, 10),  # ~39 days after event
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid is None

    def test_skip_upcoming(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-03-01", "2026-03-02", status="upcoming"),
        ]
        item = {
            "title": "Preview at Snowbird",
            "link": "https://example.com/post/preview-at-snowbird",
            "slug": "preview-at-snowbird",
            "pub_date": date(2026, 2, 10),
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid is None

    def test_prefer_most_recent(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-01-28", "2026-01-29"),
            self._make_event("imd-200", "Snowbird", "2026-02-05", "2026-02-06"),
        ]
        item = {
            "title": "GS at Snowbird",
            "link": "https://example.com/post/gs-at-snowbird",
            "slug": "gs-at-snowbird",
            "pub_date": date(2026, 2, 10),
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid == "imd-200"

    def test_no_pub_date(self):
        events = [
            self._make_event("imd-100", "Snowbird", "2026-02-08", "2026-02-09"),
        ]
        item = {
            "title": "GS at Snowbird",
            "link": "https://example.com/post/gs-at-snowbird",
            "slug": "gs-at-snowbird",
            "pub_date": None,
        }
        eid, venue = _match_blog_to_event(item, events, self.slug_map)
        assert eid is None


# --- RSS Fetch ---

SAMPLE_RSS = """\
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Blog</title>
    <item>
      <title>GS at Snowbird</title>
      <link>https://www.example.com/post/gs-at-snowbird</link>
      <pubDate>Mon, 10 Feb 2026 00:00:00 GMT</pubDate>
    </item>
    <item>
      <title>Kombi at UOP</title>
      <link>https://www.example.com/post/kombi-at-uop</link>
      <pubDate>Sun, 15 Feb 2026 12:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


class TestFetchRSSItems:
    def test_parse_rss(self):
        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.blog_linker.requests.get", return_value=mock_resp):
            items = _fetch_rss_items("https://example.com/feed.xml")

        assert len(items) == 2
        assert items[0]["title"] == "GS at Snowbird"
        assert items[0]["slug"] == "gs-at-snowbird"
        assert items[0]["pub_date"] == date(2026, 2, 10)
        assert items[1]["title"] == "Kombi at UOP"
        assert items[1]["slug"] == "kombi-at-uop"
        assert items[1]["pub_date"] == date(2026, 2, 15)

    def test_http_error(self):
        with patch("ingestion.blog_linker.requests.get", side_effect=Exception("timeout")):
            items = _fetch_rss_items("https://example.com/feed.xml")
        assert items == []

    def test_malformed_xml(self):
        mock_resp = MagicMock()
        mock_resp.text = "not xml at all"
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.blog_linker.requests.get", return_value=mock_resp):
            items = _fetch_rss_items("https://example.com/feed.xml")
        assert items == []


# --- End-to-end discover ---

class TestDiscoverBlogLinks:
    def test_preserves_manual_entries(self, tmp_path):
        """Manual entries in blog_links.json should not be overwritten."""
        blog_links_path = tmp_path / "blog_links.json"
        manual_entry = {
            "imd-100": [
                {"date": "2026-02-09", "title": "Manual Post", "url": "https://example.com/manual"}
            ]
        }
        blog_links_path.write_text(json.dumps(manual_entry))

        events = [
            {
                "id": "imd-100",
                "venue": "Snowbird",
                "dates": {"start": "2026-02-08", "end": "2026-02-09"},
                "status": "completed",
            },
        ]

        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.blog_linker.requests.get", return_value=mock_resp), \
             patch("ingestion.blog_linker.BLOG_LINKS_PATH", blog_links_path):
            result = discover_blog_links(events)

        # Manual entry preserved
        urls = [e["url"] for e in result["imd-100"]]
        assert "https://example.com/manual" in urls
        # New entry added
        assert "https://www.example.com/post/gs-at-snowbird" in urls

    def test_no_duplicate_urls(self, tmp_path):
        """Same URL should not be added twice."""
        blog_links_path = tmp_path / "blog_links.json"
        existing = {
            "imd-100": [
                {
                    "date": "2026-02-10",
                    "title": "GS at Snowbird",
                    "url": "https://www.example.com/post/gs-at-snowbird",
                }
            ]
        }
        blog_links_path.write_text(json.dumps(existing))

        events = [
            {
                "id": "imd-100",
                "venue": "Snowbird",
                "dates": {"start": "2026-02-08", "end": "2026-02-09"},
                "status": "completed",
            },
        ]

        mock_resp = MagicMock()
        mock_resp.text = SAMPLE_RSS
        mock_resp.raise_for_status = MagicMock()

        with patch("ingestion.blog_linker.requests.get", return_value=mock_resp), \
             patch("ingestion.blog_linker.BLOG_LINKS_PATH", blog_links_path):
            result = discover_blog_links(events)

        # Should still have only 1 entry — no duplicate
        snowbird_urls = [e["url"] for e in result["imd-100"]
                         if e["url"] == "https://www.example.com/post/gs-at-snowbird"]
        assert len(snowbird_urls) == 1
