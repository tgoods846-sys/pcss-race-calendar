"""Tests for social media caption generation."""

import pytest
from pathlib import Path

from social.captions import (
    _format_disciplines,
    _venue_hashtag,
    _write_caption_file,
    generate_event_captions,
    generate_weekly_caption,
    generate_weekend_caption,
)


# -- Fixtures --

@pytest.fixture
def sample_event():
    return {
        "id": "imd-test-001",
        "name": "Jr. IMC U14 Qualifier / David Wright - 1SL/2GS- Park City",
        "dates": {
            "start": "2026-02-28",
            "end": "2026-03-02",
            "display": "Feb 28-Mar 2, 2026",
        },
        "venue": "Park City",
        "state": "UT",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 2},
        "circuit": "IMD",
        "series": "IMC",
        "age_groups": ["U14", "U16"],
        "status": "upcoming",
        "pcss_relevant": True,
    }


@pytest.fixture
def snowbird_event():
    return {
        "id": "imd-test-snowbird",
        "name": "South Series GS - 2GS- Snowbird",
        "dates": {
            "start": "2026-02-09",
            "end": "2026-02-10",
            "display": "Feb 9-10, 2026",
        },
        "venue": "Snowbird",
        "state": "UT",
        "disciplines": ["GS"],
        "discipline_counts": {"GS": 2},
        "circuit": "IMD",
        "series": "South Series",
        "age_groups": ["U14", "U16"],
        "status": "upcoming",
        "pcss_relevant": True,
    }


@pytest.fixture
def minimal_event():
    return {
        "id": "imd-test-min",
        "name": "Test Race",
        "dates": {"start": "2026-03-01", "end": "2026-03-01", "display": "Mar 1, 2026"},
        "venue": "TBD",
        "state": "",
        "disciplines": [],
        "discipline_counts": {},
        "circuit": "",
        "series": "",
        "age_groups": [],
        "status": "upcoming",
        "pcss_relevant": False,
    }


@pytest.fixture
def completed_snowbird_event():
    """A completed event at Snowbird with blog recaps."""
    return {
        "id": "imd-old-snowbird",
        "name": "Old Race at Snowbird",
        "dates": {"start": "2026-01-10", "end": "2026-01-11", "display": "Jan 10-11, 2026"},
        "venue": "Snowbird",
        "state": "UT",
        "disciplines": ["SL"],
        "discipline_counts": {"SL": 1},
        "circuit": "IMD",
        "series": "",
        "age_groups": [],
        "status": "completed",
        "blog_recap_urls": [
            {"date": "2026-01-10", "title": "Snowbird Recap", "url": "https://example.com/recap"}
        ],
    }


# -- _format_disciplines --

class TestFormatDisciplines:
    def test_single_discipline(self):
        event = {"discipline_counts": {"GS": 1}}
        assert _format_disciplines(event) == "GS"

    def test_multiple_with_counts(self):
        event = {"discipline_counts": {"SL": 1, "GS": 2}}
        result = _format_disciplines(event)
        assert "SL" in result
        assert "2x GS" in result

    def test_empty(self):
        assert _format_disciplines({}) == ""
        assert _format_disciplines({"discipline_counts": {}}) == ""

    def test_all_multi_count(self):
        event = {"discipline_counts": {"SL": 3, "GS": 2}}
        result = _format_disciplines(event)
        assert "3x SL" in result
        assert "2x GS" in result


# -- _venue_hashtag --

class TestVenueHashtag:
    def test_single_word(self):
        assert _venue_hashtag("Snowbird") == "#Snowbird"

    def test_multi_word(self):
        assert _venue_hashtag("Utah Olympic Park") == "#UtahOlympicPark"

    def test_dot_venue(self):
        assert _venue_hashtag("Mt. Bachelor") == "#MtBachelor"

    def test_empty(self):
        assert _venue_hashtag("") == ""

    def test_tbd(self):
        assert _venue_hashtag("TBD") == ""

    def test_slash_venue(self):
        assert _venue_hashtag("Snowbird/Utah Olympic Park") == "#SnowbirdUtahOlympicPark"


# -- generate_event_captions --

class TestEventCaptions:
    def test_pre_race_includes_venue_and_date(self, sample_event):
        captions = generate_event_captions(sample_event)
        ig = captions["pre_race"]["instagram"]
        assert "Park City" in ig
        assert "Feb 28-Mar 2, 2026" in ig

    def test_pre_race_includes_disciplines(self, sample_event):
        captions = generate_event_captions(sample_event)
        ig = captions["pre_race"]["instagram"]
        assert "SL" in ig
        assert "2x GS" in ig

    def test_race_day_includes_race_day(self, sample_event):
        captions = generate_event_captions(sample_event)
        ig = captions["race_day"]["instagram"]
        assert "race day" in ig.lower()

    def test_blog_intro_is_short(self, sample_event):
        captions = generate_event_captions(sample_event)
        # blog_intro should be 1-2 sentences, no hashtags
        assert "#" not in captions["blog_intro"]
        assert len(captions["blog_intro"]) < 300

    def test_historical_context_when_recap_exists(self, snowbird_event, completed_snowbird_event):
        all_events = [snowbird_event, completed_snowbird_event]
        captions = generate_event_captions(snowbird_event, all_events)
        ig = captions["pre_race"]["instagram"]
        assert "recap" in ig.lower()
        assert "Snowbird" in ig

    def test_no_historical_context_without_recap(self, sample_event):
        captions = generate_event_captions(sample_event, [sample_event])
        ig = captions["pre_race"]["instagram"]
        assert "recap" not in ig.lower()

    def test_minimal_event(self, minimal_event):
        """Minimal event should not crash and should produce valid captions."""
        captions = generate_event_captions(minimal_event)
        assert captions["pre_race"]["instagram"]
        assert captions["race_day"]["instagram"]
        assert captions["blog_intro"]

    def test_all_sections_present(self, sample_event):
        captions = generate_event_captions(sample_event)
        assert "pre_race" in captions
        assert "race_day" in captions
        assert "blog_intro" in captions
        for section in ("pre_race", "race_day"):
            assert "instagram" in captions[section]
            assert "facebook" in captions[section]
            assert "short" in captions[section]

    def test_facebook_has_no_hashtags(self, sample_event):
        captions = generate_event_captions(sample_event)
        fb = captions["pre_race"]["facebook"]
        assert "#" not in fb

    def test_instagram_has_hashtags(self, sample_event):
        captions = generate_event_captions(sample_event)
        ig = captions["pre_race"]["instagram"]
        assert "#" in ig


# -- generate_weekly_caption --

class TestWeeklyCaptions:
    def test_lists_all_events(self, sample_event, snowbird_event):
        result = generate_weekly_caption([sample_event, snowbird_event])
        ig = result["instagram"]
        assert "Park City" in ig
        assert "Snowbird" in ig
        assert "#PCSkiRacing" in ig

    def test_single_event(self, sample_event):
        result = generate_weekly_caption([sample_event])
        assert "Park City" in result["instagram"]

    def test_empty_events(self):
        result = generate_weekly_caption([])
        assert result["instagram"] == ""
        assert result["facebook"] == ""
        assert result["short"] == ""

    def test_facebook_no_hashtags(self, sample_event):
        result = generate_weekly_caption([sample_event])
        assert "#" not in result["facebook"]

    def test_short_no_hashtags(self, sample_event):
        result = generate_weekly_caption([sample_event])
        assert "#" not in result["short"]


# -- generate_weekend_caption --

class TestWeekendCaptions:
    def test_lists_events(self, sample_event, snowbird_event):
        result = generate_weekend_caption([sample_event, snowbird_event])
        ig = result["instagram"]
        assert "weekend" in ig.lower()
        assert "#PCSkiRacing" in ig

    def test_empty_events(self):
        result = generate_weekend_caption([])
        assert result["instagram"] == ""


# -- _write_caption_file --

class TestWriteCaptionFile:
    def test_writes_correct_sections(self, tmp_path):
        path = tmp_path / "captions.txt"
        sections = {
            "instagram": "IG content here",
            "facebook": "FB content here",
            "short": "Short blurb",
        }
        result = _write_caption_file(path, sections)
        assert result == path
        content = path.read_text()
        assert "=== INSTAGRAM ===" in content
        assert "IG content here" in content
        assert "=== FACEBOOK ===" in content
        assert "FB content here" in content
        assert "=== SHORT ===" in content
        assert "Short blurb" in content

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "nested" / "dir" / "captions.txt"
        sections = {"test": "content"}
        _write_caption_file(path, sections)
        assert path.exists()

    def test_file_ends_with_newline(self, tmp_path):
        path = tmp_path / "captions.txt"
        sections = {"test": "content"}
        _write_caption_file(path, sections)
        content = path.read_text()
        assert content.endswith("\n")
