"""Tests for .ics calendar feed generation."""

import json
import tempfile
from pathlib import Path

import pytest

from ingestion.ics_feed import generate_feed


def _make_database(events, generated_at="2026-01-15T10:30:00"):
    """Create a temporary race database JSON file."""
    data = {
        "generated_at": generated_at,
        "source": "test",
        "event_count": len(events),
        "events": events,
    }
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
    json.dump(data, tmp)
    tmp.flush()
    return Path(tmp.name)


def _make_event(**overrides):
    """Create a test event with defaults."""
    event = {
        "id": "imd-1234",
        "name": "Test Race - SL/GS - Snowbasin",
        "dates": {"start": "2026-02-14", "end": "2026-02-15", "display": "Feb 14-15, 2026"},
        "venue": "Snowbasin",
        "state": "UT",
        "disciplines": ["SL", "GS"],
        "circuit": "IMD",
        "status": "upcoming",
        "source_url": "https://imdalpine.org/event/test/",
        "description": "",
    }
    event.update(overrides)
    return event


def _generate_with_events(events, generated_at="2026-01-15T10:30:00"):
    """Generate .ics content from a list of test events."""
    db_path = _make_database(events, generated_at)
    out_path = Path(tempfile.mkdtemp()) / "test.ics"
    content = generate_feed(database_path=db_path, output_path=out_path)
    db_path.unlink()
    return content


class TestCalendarStructure:
    def test_begins_with_vcalendar(self):
        content = _generate_with_events([_make_event()])
        assert content.startswith("BEGIN:VCALENDAR\r\n")

    def test_ends_with_vcalendar(self):
        content = _generate_with_events([_make_event()])
        assert content.strip().endswith("END:VCALENDAR")

    def test_version_present(self):
        content = _generate_with_events([_make_event()])
        assert "VERSION:2.0\r\n" in content

    def test_prodid_present(self):
        content = _generate_with_events([_make_event()])
        assert "PRODID:-//Sim.Sports//Race Calendar//EN\r\n" in content

    def test_calname_present(self):
        content = _generate_with_events([_make_event()])
        assert "X-WR-CALNAME:IMD Youth Ski Race Calendar\r\n" in content

    def test_method_publish(self):
        content = _generate_with_events([_make_event()])
        assert "METHOD:PUBLISH\r\n" in content

    def test_refresh_interval(self):
        content = _generate_with_events([_make_event()])
        assert "REFRESH-INTERVAL;VALUE=DURATION:PT12H\r\n" in content
        assert "X-PUBLISHED-TTL:PT12H\r\n" in content


class TestEventFormatting:
    def test_uid_format(self):
        content = _generate_with_events([_make_event(id="imd-1234")])
        assert "UID:imd-1234@sim.sports\r\n" in content

    def test_dtend_exclusive(self):
        """DTEND should be end date + 1 day (exclusive per RFC 5545)."""
        content = _generate_with_events([
            _make_event(dates={"start": "2026-02-14", "end": "2026-02-15", "display": ""})
        ])
        assert "DTSTART;VALUE=DATE:20260214\r\n" in content
        assert "DTEND;VALUE=DATE:20260216\r\n" in content  # 15th + 1 = 16th

    def test_single_day_event(self):
        """Single-day event: DTEND = start + 1."""
        content = _generate_with_events([
            _make_event(dates={"start": "2026-03-01", "end": "2026-03-01", "display": ""})
        ])
        assert "DTSTART;VALUE=DATE:20260301\r\n" in content
        assert "DTEND;VALUE=DATE:20260302\r\n" in content

    def test_summary_escaped(self):
        content = _generate_with_events([_make_event(name="Race, with; special\\chars")])
        assert "SUMMARY:Race\\, with\\; special\\\\chars\r\n" in content

    def test_location_with_state(self):
        content = _generate_with_events([_make_event(venue="Snowbasin", state="UT")])
        assert "LOCATION:Snowbasin\\, UT\r\n" in content

    def test_location_without_state(self):
        content = _generate_with_events([_make_event(venue="Snowbasin", state="")])
        assert "LOCATION:Snowbasin\r\n" in content

    def test_description_includes_disciplines(self):
        content = _generate_with_events([_make_event(disciplines=["SL", "GS"])])
        assert "Disciplines: SL\\, GS" in content

    def test_description_includes_circuit(self):
        content = _generate_with_events([_make_event(circuit="IMD")])
        assert "Circuit: IMD" in content

    def test_source_url_as_url_property(self):
        content = _generate_with_events([
            _make_event(source_url="https://imdalpine.org/event/test/")
        ])
        assert "URL:https://imdalpine.org/event/test/\r\n" in content


class TestCanceledEvents:
    def test_canceled_status(self):
        content = _generate_with_events([_make_event(status="canceled")])
        assert "STATUS:CANCELLED\r\n" in content

    def test_upcoming_no_status_line(self):
        content = _generate_with_events([_make_event(status="upcoming")])
        assert "STATUS:" not in content

    def test_completed_no_status_line(self):
        content = _generate_with_events([_make_event(status="completed")])
        assert "STATUS:" not in content


class TestValarm:
    def test_valarm_present(self):
        content = _generate_with_events([_make_event()])
        assert "BEGIN:VALARM\r\n" in content
        assert "END:VALARM\r\n" in content

    def test_trigger_one_day_before(self):
        content = _generate_with_events([_make_event()])
        assert "TRIGGER:-P1D\r\n" in content

    def test_action_display(self):
        content = _generate_with_events([_make_event()])
        assert "ACTION:DISPLAY\r\n" in content


class TestDtstamp:
    def test_uses_generated_at(self):
        """DTSTAMP should use database generated_at, not current time."""
        content = _generate_with_events(
            [_make_event()],
            generated_at="2026-01-15T10:30:00",
        )
        assert "DTSTAMP:20260115T103000Z\r\n" in content

    def test_deterministic_output(self):
        """Same input should produce identical output."""
        events = [_make_event()]
        content1 = _generate_with_events(events, "2026-01-15T10:30:00")
        content2 = _generate_with_events(events, "2026-01-15T10:30:00")
        assert content1 == content2


class TestMultipleEvents:
    def test_multiple_events_each_have_vevent(self):
        events = [
            _make_event(id="imd-1001", name="Race One"),
            _make_event(id="imd-1002", name="Race Two"),
            _make_event(id="imd-1003", name="Race Three"),
        ]
        content = _generate_with_events(events)
        assert content.count("BEGIN:VEVENT") == 3
        assert content.count("END:VEVENT") == 3
        assert "UID:imd-1001@sim.sports" in content
        assert "UID:imd-1002@sim.sports" in content
        assert "UID:imd-1003@sim.sports" in content

    def test_empty_database(self):
        content = _generate_with_events([])
        assert "BEGIN:VCALENDAR" in content
        assert "END:VCALENDAR" in content
        assert "BEGIN:VEVENT" not in content


class TestLineEndings:
    def test_crlf_line_endings(self):
        """RFC 5545 requires CRLF line endings."""
        content = _generate_with_events([_make_event()])
        # Split on \r\n — all lines should end with \r\n
        lines = content.split("\r\n")
        assert len(lines) > 5  # sanity check
        # No bare \n should exist (after removing \r\n)
        cleaned = content.replace("\r\n", "")
        assert "\n" not in cleaned


class TestTextEscaping:
    def test_backslash_escaped(self):
        content = _generate_with_events([_make_event(name="Race \\ test")])
        assert "SUMMARY:Race \\\\ test" in content

    def test_semicolon_escaped(self):
        content = _generate_with_events([_make_event(name="Race; test")])
        assert "SUMMARY:Race\\; test" in content

    def test_comma_escaped(self):
        content = _generate_with_events([_make_event(name="Race, test")])
        assert "SUMMARY:Race\\, test" in content

    def test_newline_escaped(self):
        content = _generate_with_events([_make_event(name="Race\ntest")])
        assert "SUMMARY:Race\\ntest" in content


class TestFileOutput:
    def test_writes_file(self):
        db_path = _make_database([_make_event()])
        out_path = Path(tempfile.mkdtemp()) / "output.ics"
        generate_feed(database_path=db_path, output_path=out_path)
        assert out_path.exists()
        content = out_path.read_text()
        assert content.startswith("BEGIN:VCALENDAR")
        db_path.unlink()

    def test_skips_events_without_dates(self):
        events = [
            _make_event(id="imd-good"),
            _make_event(id="imd-bad", dates={"start": "", "end": "", "display": ""}),
        ]
        content = _generate_with_events(events)
        assert "UID:imd-good@sim.sports" in content
        assert "UID:imd-bad@sim.sports" not in content
