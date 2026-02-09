"""Tests for social media image generation templates."""

import pytest
from social.config import FORMATS
from social.templates.pre_race import PreRaceTemplate
from social.templates.race_day import RaceDayTemplate
from social.templates.weekly_preview import WeeklyPreviewTemplate


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
        "pcss_confirmed": False,
    }


@pytest.fixture
def snowbird_event():
    """Event at Snowbird — has a matching venue photo."""
    return {
        "id": "imd-test-snowbird",
        "name": "Snowbird Open SL/GS",
        "dates": {
            "start": "2026-03-07",
            "end": "2026-03-08",
            "display": "Mar 7-8, 2026",
        },
        "venue": "Snowbird",
        "state": "UT",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 1},
        "circuit": "IMD",
        "series": "",
        "age_groups": [],
        "status": "upcoming",
        "pcss_relevant": True,
    }


@pytest.fixture
def unknown_venue_event():
    """Event at venue with no matching photo — should use default."""
    return {
        "id": "imd-test-unknown",
        "name": "Mystery Mountain Race",
        "dates": {
            "start": "2026-03-15",
            "end": "2026-03-15",
            "display": "Mar 15, 2026",
        },
        "venue": "Mystery Mountain",
        "state": "XX",
        "disciplines": ["GS"],
        "discipline_counts": {"GS": 1},
        "circuit": "IMD",
        "series": "",
        "age_groups": [],
        "status": "upcoming",
        "pcss_relevant": False,
    }


@pytest.fixture
def minimal_event():
    """Event with no disciplines, no age groups, no state."""
    return {
        "id": "imd-test-002",
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
def long_name_event():
    """Event with a very long name that requires wrapping."""
    return {
        "id": "imd-test-003",
        "name": "Western Region Junior Championships Super Giant Slalom and Downhill Combined Event - Mission Ridge Resort",
        "dates": {"start": "2026-03-12", "end": "2026-03-17", "display": "Mar 12-17, 2026"},
        "venue": "Mission Ridge",
        "state": "WA",
        "disciplines": ["SL", "GS", "SG", "DH", "AC", "PS"],
        "discipline_counts": {"SL": 1, "GS": 1, "SG": 1, "DH": 1, "AC": 1, "PS": 1},
        "circuit": "Western Region",
        "series": "Western Region",
        "age_groups": ["U14", "U16", "U18", "U21"],
        "status": "upcoming",
        "pcss_relevant": True,
    }


@pytest.fixture
def multiple_events(sample_event, minimal_event, long_name_event):
    return [sample_event, minimal_event, long_name_event]


# -- Dimension tests --

class TestPreRaceTemplate:
    @pytest.mark.parametrize("fmt,expected", list(FORMATS.items()))
    def test_dimensions(self, fmt, expected, sample_event):
        template = PreRaceTemplate(fmt)
        img = template.render(event=sample_event)
        assert img.size == expected

    def test_no_disciplines(self, minimal_event):
        template = PreRaceTemplate("story")
        img = template.render(event=minimal_event)
        assert img.size == (1080, 1920)

    def test_many_disciplines(self, long_name_event):
        template = PreRaceTemplate("story")
        img = template.render(event=long_name_event)
        assert img.size == (1080, 1920)

    def test_venue_photo_match(self, snowbird_event):
        """Event with matching venue photo should render without error."""
        template = PreRaceTemplate("story")
        img = template.render(event=snowbird_event)
        assert img.size == (1080, 1920)

    def test_venue_photo_fallback(self, unknown_venue_event):
        """Event with unknown venue should fall back to default."""
        template = PreRaceTemplate("post")
        img = template.render(event=unknown_venue_event)
        assert img.size == (1080, 1080)

    def test_compact_format(self, sample_event):
        """Facebook format should render at correct dimensions."""
        template = PreRaceTemplate("facebook")
        img = template.render(event=sample_event)
        assert img.size == (1200, 630)


class TestRaceDayTemplate:
    @pytest.mark.parametrize("fmt,expected", list(FORMATS.items()))
    def test_dimensions(self, fmt, expected, sample_event):
        template = RaceDayTemplate(fmt)
        img = template.render(event=sample_event)
        assert img.size == expected

    def test_venue_photo_match(self, snowbird_event):
        """Event with matching venue photo should render without error."""
        template = RaceDayTemplate("story")
        img = template.render(event=snowbird_event)
        assert img.size == (1080, 1920)

    def test_venue_photo_fallback(self, unknown_venue_event):
        """Event with unknown venue should fall back to default."""
        template = RaceDayTemplate("post")
        img = template.render(event=unknown_venue_event)
        assert img.size == (1080, 1080)

    def test_no_disciplines(self, minimal_event):
        """Minimal event should render without error."""
        template = RaceDayTemplate("story")
        img = template.render(event=minimal_event)
        assert img.size == (1080, 1920)


class TestWeeklyPreviewTemplate:
    @pytest.mark.parametrize("fmt,expected", list(FORMATS.items()))
    def test_dimensions(self, fmt, expected, multiple_events):
        template = WeeklyPreviewTemplate(fmt)
        img = template.render(events=multiple_events)
        assert img.size == expected

    def test_single_event(self, sample_event):
        """Should handle a single event."""
        template = WeeklyPreviewTemplate("story")
        img = template.render(events=[sample_event])
        assert img.size == (1080, 1920)

    def test_five_events(self, sample_event):
        """Should handle five events without overflow."""
        events = [sample_event.copy() for _ in range(5)]
        for i, e in enumerate(events):
            e["id"] = f"imd-test-{i}"
            e["name"] = f"Event {i+1} - Race"
        template = WeeklyPreviewTemplate("story")
        img = template.render(events=events)
        assert img.size == (1080, 1920)

    def test_empty_events(self):
        """Should handle empty event list gracefully."""
        template = WeeklyPreviewTemplate("post")
        img = template.render(events=[])
        assert img.size == (1080, 1080)

    def test_uses_default_venue(self, multiple_events):
        """Weekly preview uses default/gradient venue photo."""
        template = WeeklyPreviewTemplate("story")
        img = template.render(events=multiple_events)
        assert img.size == (1080, 1920)
