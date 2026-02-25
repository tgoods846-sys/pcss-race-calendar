"""Tests for social posting scheduler."""

from datetime import date
from unittest.mock import patch

from social.scheduler import get_todays_tasks, is_posted, load_posting_log, save_posting_log


def _make_event(event_id, start, end=None, pcss_relevant=True):
    """Helper to build a minimal event dict."""
    return {
        "id": event_id,
        "name": f"Test Event {event_id}",
        "dates": {
            "start": start,
            "end": end or start,
            "display": start,
        },
        "venue": "Test Venue",
        "pcss_relevant": pcss_relevant,
    }


class TestGetTodaysTasks:
    def test_monday_posts_weekly(self):
        """Monday with events returns weekly_preview task."""
        monday = date(2026, 2, 23)  # A Monday
        events = [_make_event("e1", "2026-02-25", "2026-02-27")]

        with patch("social.generate.date") as mock_date:
            mock_date.today.return_value = monday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            tasks = get_todays_tasks(events, {"posts": []}, ref_date=monday)

        types = [t["type"] for t in tasks]
        assert "weekly_preview" in types
        # Key should reference the Monday date
        weekly = [t for t in tasks if t["type"] == "weekly_preview"][0]
        assert weekly["key"] == "weekly_preview:2026-02-23"

    def test_thursday_posts_weekend(self):
        """Thursday with weekend events returns weekend_preview task."""
        thursday = date(2026, 2, 26)  # A Thursday
        # Event on Saturday Feb 28
        events = [_make_event("e1", "2026-02-28")]

        with patch("social.generate.date") as mock_date:
            mock_date.today.return_value = thursday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            tasks = get_todays_tasks(events, {"posts": []}, ref_date=thursday)

        types = [t["type"] for t in tasks]
        assert "weekend_preview" in types
        weekend = [t for t in tasks if t["type"] == "weekend_preview"][0]
        # Friday is Feb 27
        assert weekend["key"] == "weekend_preview:2026-02-27"

    def test_pre_race_two_days_before(self):
        """Event starting in 2 days returns pre_race task."""
        today = date(2026, 2, 25)  # Wednesday
        events = [_make_event("e1", "2026-02-27", "2026-02-28")]

        tasks = get_todays_tasks(events, {"posts": []}, ref_date=today)

        types = [t["type"] for t in tasks]
        assert "pre_race" in types
        pre = [t for t in tasks if t["type"] == "pre_race"][0]
        assert pre["key"] == "pre_race:e1"

    def test_race_day_on_start(self):
        """Event starting today returns race_day task."""
        today = date(2026, 2, 25)
        events = [_make_event("e1", "2026-02-25", "2026-02-27")]

        tasks = get_todays_tasks(events, {"posts": []}, ref_date=today)

        types = [t["type"] for t in tasks]
        assert "race_day" in types
        rd = [t for t in tasks if t["type"] == "race_day"][0]
        assert rd["key"] == "race_day:e1"

    def test_no_events_no_tasks(self):
        """No matching events returns empty list."""
        today = date(2026, 2, 25)  # Wednesday
        # Event in the past
        events = [_make_event("e1", "2026-01-10", "2026-01-12")]

        tasks = get_todays_tasks(events, {"posts": []}, ref_date=today)
        assert tasks == []

    def test_already_posted_skipped(self):
        """Item in posting log not returned again."""
        today = date(2026, 2, 25)
        events = [_make_event("e1", "2026-02-25", "2026-02-27")]

        log = {"posts": [{"key": "race_day:e1", "content_type": "race_day"}]}
        tasks = get_todays_tasks(events, log, ref_date=today)

        keys = [t["key"] for t in tasks]
        assert "race_day:e1" not in keys

    def test_multiple_tasks_same_day(self):
        """Thursday with race-day event returns both weekend_preview and race_day."""
        thursday = date(2026, 2, 26)
        events = [
            # Event starting today (race day)
            _make_event("e1", "2026-02-26", "2026-02-28"),
            # Event this weekend
            _make_event("e2", "2026-02-27", "2026-02-28"),
        ]

        with patch("social.generate.date") as mock_date:
            mock_date.today.return_value = thursday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            tasks = get_todays_tasks(events, {"posts": []}, ref_date=thursday)

        types = [t["type"] for t in tasks]
        assert "weekend_preview" in types
        assert "race_day" in types

    def test_tuesday_no_weekly_or_weekend(self):
        """Non-Monday/Thursday returns no preview tasks."""
        tuesday = date(2026, 2, 24)  # A Tuesday
        events = [_make_event("e1", "2026-02-28", "2026-03-01")]

        with patch("social.generate.date") as mock_date:
            mock_date.today.return_value = tuesday
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            tasks = get_todays_tasks(events, {"posts": []}, ref_date=tuesday)

        types = [t["type"] for t in tasks]
        assert "weekly_preview" not in types
        assert "weekend_preview" not in types


class TestPostingLog:
    def test_load_save_roundtrip(self, tmp_path, monkeypatch):
        """Posting log can be saved and loaded."""
        log_path = tmp_path / "posting_log.json"
        monkeypatch.setattr("social.scheduler.POSTING_LOG_PATH", log_path)

        log = {"posts": [{"key": "test:1", "content_type": "test"}]}
        save_posting_log(log)

        loaded = load_posting_log()
        assert loaded["posts"][0]["key"] == "test:1"

    def test_load_missing_file(self, tmp_path, monkeypatch):
        """Loading a missing log returns empty structure."""
        log_path = tmp_path / "does_not_exist.json"
        monkeypatch.setattr("social.scheduler.POSTING_LOG_PATH", log_path)

        log = load_posting_log()
        assert log == {"posts": []}

    def test_is_posted(self):
        log = {"posts": [{"key": "weekly_preview:2026-02-23"}]}
        assert is_posted(log, "weekly_preview:2026-02-23") is True
        assert is_posted(log, "weekly_preview:2026-03-02") is False
