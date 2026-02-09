"""Fetch and parse the IMD Alpine iCal feed into structured race events."""

from datetime import date, timedelta
from icalendar import Calendar
import requests

from ingestion.config import IMD_ICAL_URL, IMD_ICAL_PAST_URL
from ingestion.summary_parser import parse_summary


def fetch_ical(url: str = IMD_ICAL_URL) -> str:
    """Fetch the iCal feed content."""
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def parse_ical(ical_text: str) -> list:
    """Parse iCal text into a list of raw event dicts.

    Each dict contains fields extracted directly from the VEVENT plus
    parsed SUMMARY fields (event_name, disciplines, venue, etc.).
    """
    cal = Calendar.from_ical(ical_text)
    events = []

    for component in cal.walk():
        if component.name != "VEVENT":
            continue

        # Extract raw fields
        uid = str(component.get("UID", ""))
        summary = str(component.get("SUMMARY", ""))
        description = str(component.get("DESCRIPTION", ""))
        url = str(component.get("URL", ""))
        location_raw = str(component.get("LOCATION", ""))

        # Parse dates — DTEND is exclusive in iCal spec, subtract 1 day
        dtstart_raw = component.get("DTSTART")
        dtend_raw = component.get("DTEND")

        if dtstart_raw is None:
            continue

        dtstart = dtstart_raw.dt
        if isinstance(dtstart, date) and not hasattr(dtstart, "hour"):
            start_date = dtstart
        else:
            start_date = dtstart.date() if hasattr(dtstart, "date") else dtstart

        if dtend_raw:
            dtend = dtend_raw.dt
            if isinstance(dtend, date) and not hasattr(dtend, "hour"):
                end_date = dtend - timedelta(days=1)  # Exclusive end → inclusive
            else:
                end_date = dtend.date() if hasattr(dtend, "date") else dtend
        else:
            end_date = start_date

        # Ensure end is not before start (single-day events)
        if end_date < start_date:
            end_date = start_date

        # Extract categories
        categories = []
        cat_prop = component.get("CATEGORIES")
        if cat_prop:
            if isinstance(cat_prop, list):
                for cat in cat_prop:
                    categories.extend([str(c) for c in cat.cats])
            else:
                categories.extend([str(c) for c in cat_prop.cats])

        # Parse TD name from LOCATION field (format: "TD- Name" or "TD- Name/ Name")
        td_name = ""
        if location_raw and location_raw.lower().startswith("td"):
            td_name = location_raw.replace("TD-", "").replace("TD -", "").strip()
            td_name = td_name.lstrip("- ").strip()

        # Parse SUMMARY for structured fields
        parsed = parse_summary(summary)

        # Clean description (remove escaped commas from iCal format)
        clean_desc = description.replace("\\,", ",").replace("\\n", "\n").strip()
        if clean_desc.lower() == "none":
            clean_desc = ""

        events.append({
            "uid": uid,
            "summary_raw": summary,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "event_name": parsed["event_name"],
            "venue": parsed["venue"],
            "disciplines": parsed["disciplines"],
            "discipline_counts": parsed["discipline_counts"],
            "canceled": parsed["canceled"],
            "categories": categories,
            "td_name": td_name,
            "description": clean_desc,
            "source_url": url,
        })

    return events


def fetch_and_parse(url: str = IMD_ICAL_URL) -> list:
    """Fetch the IMD iCal feed (upcoming + past) and return parsed events."""
    # Fetch upcoming events
    ical_text = fetch_ical(url)
    events = parse_ical(ical_text)

    # Fetch past events and merge (deduplicate by UID)
    try:
        past_text = fetch_ical(IMD_ICAL_PAST_URL)
        past_events = parse_ical(past_text)
        seen_uids = {e["uid"] for e in events}
        for pe in past_events:
            if pe["uid"] not in seen_uids:
                seen_uids.add(pe["uid"])
                events.append(pe)
    except Exception as exc:
        print(f"  Warning: could not fetch past events: {exc}")

    return events
