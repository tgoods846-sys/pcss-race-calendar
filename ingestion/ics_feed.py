"""Generate a subscribable .ics calendar feed from the race database.

Reads data/race_database.json and writes site/pcss-calendar.ics.
Calendar apps can subscribe to the hosted URL and get automatic updates.

Usage: python3 -m ingestion.ics_feed
"""

import json
from datetime import datetime, timedelta
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATABASE_PATH = PROJECT_ROOT / "data" / "race_database.json"
OUTPUT_PATH = PROJECT_ROOT / "site" / "pcss-calendar.ics"

CALENDAR_NAME = "IMD Youth Ski Race Calendar"
CALENDAR_PRODID = "-//Sim.Sports//Race Calendar//EN"


def _escape_ics(text: str) -> str:
    """Escape text per RFC 5545 section 3.3.11."""
    if not text:
        return ""
    return (
        text.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _add_one_day(iso_date: str) -> str:
    """Add one day to ISO date string. DTEND is exclusive in RFC 5545."""
    d = datetime.strptime(iso_date, "%Y-%m-%d") + timedelta(days=1)
    return d.strftime("%Y%m%d")


def _format_date(iso_date: str) -> str:
    """Convert YYYY-MM-DD to YYYYMMDD."""
    return iso_date.replace("-", "")


def _build_location(event: dict) -> str:
    """Build location string from venue and state."""
    venue = event.get("venue", "")
    state = event.get("state", "")
    if not venue:
        return ""
    return f"{venue}, {state}" if state else venue


def _build_description(event: dict) -> str:
    """Build event description for the feed."""
    parts = []
    disciplines = event.get("disciplines", [])
    if disciplines:
        parts.append("Disciplines: " + ", ".join(disciplines))
    circuit = event.get("circuit", "")
    if circuit:
        parts.append("Circuit: " + circuit)
    source_url = event.get("source_url", "")
    if source_url:
        parts.append(source_url)
    return "\n".join(parts)


def generate_feed(database_path: Path = DATABASE_PATH, output_path: Path = OUTPUT_PATH) -> str:
    """Generate .ics feed from race database.

    Args:
        database_path: Path to race_database.json
        output_path: Path to write the .ics file

    Returns:
        The .ics content as a string.
    """
    with open(database_path) as f:
        data = json.load(f)

    events = data.get("events", [])
    generated_at = data.get("generated_at", datetime.now().isoformat(timespec="seconds"))

    # Use generated_at as DTSTAMP for deterministic output
    dtstamp = datetime.fromisoformat(generated_at).strftime("%Y%m%dT%H%M%SZ")

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{CALENDAR_PRODID}",
        f"X-WR-CALNAME:{CALENDAR_NAME}",
        "METHOD:PUBLISH",
        "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
        "X-PUBLISHED-TTL:PT12H",
    ]

    for event in events:
        start = event.get("dates", {}).get("start", "")
        end = event.get("dates", {}).get("end", "")
        if not start or not end:
            continue

        uid = f"{event['id']}@sim.sports"
        status = event.get("status", "upcoming")

        lines.append("BEGIN:VEVENT")
        lines.append(f"UID:{uid}")
        lines.append(f"DTSTAMP:{dtstamp}")
        lines.append(f"DTSTART;VALUE=DATE:{_format_date(start)}")
        lines.append(f"DTEND;VALUE=DATE:{_add_one_day(end)}")
        lines.append(f"SUMMARY:{_escape_ics(event.get('name', ''))}")
        lines.append(f"LOCATION:{_escape_ics(_build_location(event))}")
        lines.append(f"DESCRIPTION:{_escape_ics(_build_description(event))}")

        if status == "canceled":
            lines.append("STATUS:CANCELLED")

        # Source URL
        source_url = event.get("source_url", "")
        if source_url:
            lines.append(f"URL:{source_url}")

        # 1-day-before reminder
        lines.append("BEGIN:VALARM")
        lines.append("TRIGGER:-P1D")
        lines.append("ACTION:DISPLAY")
        lines.append(f"DESCRIPTION:{_escape_ics(event.get('name', ''))}")
        lines.append("END:VALARM")

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    # RFC 5545 requires CRLF line endings
    content = "\r\n".join(lines) + "\r\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", newline="") as f:
        f.write(content)

    print(f"Wrote {len(events)} events to {output_path}")
    return content


if __name__ == "__main__":
    generate_feed()
