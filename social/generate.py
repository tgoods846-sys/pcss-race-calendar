"""CLI entry point for social image generation.

Usage:
    python3 -m social.generate                     # All upcoming PCSS events
    python3 -m social.generate --type pre_race     # Only pre-race images
    python3 -m social.generate --format post        # Only Instagram post format
    python3 -m social.generate --event imd-14398   # Specific event only
    python3 -m social.generate --preview           # Open first image after generation
    python3 -m social.generate --captions-only     # Generate captions without images
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from social.captions import (
    generate_event_captions,
    generate_weekly_caption,
    generate_weekend_caption,
    _write_caption_file,
)
from social.config import FORMATS, OUTPUT_DIR, RACE_DB_PATH, TEMPLATE_TYPES
from social.templates.pre_race import PreRaceTemplate
from social.templates.race_day import RaceDayTemplate
from social.templates.weekly_preview import WeeklyPreviewTemplate
from social.templates.weekend_preview import WeekendPreviewTemplate
from social.templates.monthly_calendar import MonthlyCalendarTemplate


def load_events() -> list[dict]:
    """Load events from the race database."""
    with open(RACE_DB_PATH) as f:
        db = json.load(f)
    return db.get("events", [])


def filter_pcss_upcoming(events: list[dict]) -> list[dict]:
    """Filter to PCSS-relevant upcoming events."""
    today = date.today().isoformat()
    return [
        e for e in events
        if e.get("pcss_relevant")
        and e.get("dates", {}).get("end", "") >= today
    ]


def get_weekly_events(events: list[dict]) -> list[dict]:
    """Get PCSS events happening this week (Mon-Sun)."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    mon_str = monday.isoformat()
    sun_str = sunday.isoformat()

    return [
        e for e in events
        if e.get("pcss_relevant")
        and e.get("dates", {}).get("start", "") <= sun_str
        and e.get("dates", {}).get("end", "") >= mon_str
    ]


def get_weekend_events(events: list[dict]) -> list[dict]:
    """Get ALL events happening this weekend (Fri-Sun)."""
    today = date.today()
    # Friday of this week (weekday 4)
    days_to_friday = (4 - today.weekday()) % 7
    friday = today + timedelta(days=days_to_friday)
    sunday = friday + timedelta(days=2)
    fri_str = friday.isoformat()
    sun_str = sunday.isoformat()

    return [
        e for e in events
        if e.get("dates", {}).get("start", "") <= sun_str
        and e.get("dates", {}).get("end", "") >= fri_str
    ]


def get_pre_race_events(events: list[dict], days_ahead: int = 2, ref_date: date | None = None) -> list[dict]:
    """Get PCSS events starting in exactly N days."""
    target = (ref_date or date.today()) + timedelta(days=days_ahead)
    target_str = target.isoformat()
    return [
        e for e in events
        if e.get("pcss_relevant")
        and e.get("dates", {}).get("start", "") == target_str
    ]


def get_race_day_events(events: list[dict], ref_date: date | None = None) -> list[dict]:
    """Get PCSS events starting today."""
    today_str = (ref_date or date.today()).isoformat()
    return [
        e for e in events
        if e.get("pcss_relevant")
        and e.get("dates", {}).get("start", "") == today_str
    ]


def _event_folder_name(event: dict) -> str:
    """Build a descriptive, filesystem-safe folder name from event data.

    Example: 'WR Open FIS Race - Palisades Feb 24-27'
    """
    # Extract event title: everything before the discipline listing
    # Names follow pattern: "Title - SL/GS/SG- Venue" or "Title- 2 SL/2 GS- Venue"
    parts = re.split(r'\s*-\s*', event["name"])
    title = parts[0].strip() if parts else event["name"]

    venue = event.get("venue", "")
    display = event.get("dates", {}).get("display", "")
    # Strip year from display: "Feb 24-27, 2026" → "Feb 24-27"
    compact_date = re.sub(r',?\s*\d{4}$', '', display).strip()

    folder = f"{title} - {venue} {compact_date}" if venue else f"{title} {compact_date}"

    # Sanitize for filesystem
    folder = folder.replace("/", "-")
    folder = re.sub(r'[:\\*?"<>|]', '', folder)
    folder = re.sub(r'\s+', ' ', folder).strip()
    return folder


def generate_event_images(
    event: dict,
    types: list[str],
    formats: list[str],
    all_events: list[dict] | None = None,
    captions_only: bool = False,
) -> list[Path]:
    """Generate images for a single event. Returns list of output paths."""
    outputs = []
    event_dir = OUTPUT_DIR / _event_folder_name(event)

    if not captions_only:
        for fmt in formats:
            if "pre_race" in types:
                template = PreRaceTemplate(fmt)
                template.render(event=event)
                path = event_dir / f"pre_race_{fmt}.png"
                template.save(path)
                outputs.append(path)

            if "race_day" in types:
                template = RaceDayTemplate(fmt)
                template.render(event=event)
                path = event_dir / f"race_day_{fmt}.png"
                template.save(path)
                outputs.append(path)

    # Generate captions
    captions = generate_event_captions(event, all_events or [])
    sections = {}
    for caption_type in ("pre_race", "race_day"):
        if caption_type in types:
            sections.update({
                f"{caption_type.upper()} — INSTAGRAM": captions[caption_type]["instagram"],
                f"{caption_type.upper()} — FACEBOOK": captions[caption_type]["facebook"],
                f"{caption_type.upper()} — SHORT (Blog/Email)": captions[caption_type]["short"],
            })
    if sections:
        caption_path = _write_caption_file(event_dir / "captions.txt", sections)
        outputs.append(caption_path)

    return outputs


def generate_weekly_images(
    events: list[dict],
    formats: list[str],
    captions_only: bool = False,
) -> list[Path]:
    """Generate weekly preview images. Returns list of output paths."""
    if not events:
        return []

    today = date.today()
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    week_dir = OUTPUT_DIR / f"This Week in PC Ski Racing {monday.strftime('%b %-d')}-{sunday.strftime('%-d')}"
    outputs = []

    if not captions_only:
        for fmt in formats:
            template = WeeklyPreviewTemplate(fmt)
            template.render(events=events)
            path = week_dir / f"weekly_preview_{fmt}.png"
            template.save(path)
            outputs.append(path)

    # Generate captions
    caption_sections = generate_weekly_caption(events)
    if any(caption_sections.values()):
        sections = {
            "INSTAGRAM": caption_sections["instagram"],
            "FACEBOOK": caption_sections["facebook"],
            "SHORT (Blog/Email)": caption_sections["short"],
        }
        caption_path = _write_caption_file(week_dir / "captions.txt", sections)
        outputs.append(caption_path)

    return outputs


def generate_weekend_images(
    events: list[dict],
    formats: list[str],
    captions_only: bool = False,
) -> list[Path]:
    """Generate weekend preview images. Returns list of output paths."""
    if not events:
        return []

    today = date.today()
    days_to_friday = (4 - today.weekday()) % 7
    friday = today + timedelta(days=days_to_friday)
    sunday = friday + timedelta(days=2)
    if friday.month == sunday.month:
        date_range = f"{friday.strftime('%b %-d')}-{sunday.strftime('%-d')}"
    else:
        date_range = f"{friday.strftime('%b %-d')}-{sunday.strftime('%b %-d')}"
    week_dir = OUTPUT_DIR / f"This Weekend in PC Ski Racing {date_range}"
    outputs = []

    if not captions_only:
        for fmt in formats:
            template = WeekendPreviewTemplate(fmt)
            template.render(events=events)
            path = week_dir / f"weekend_preview_{fmt}.png"
            template.save(path)
            outputs.append(path)

    # Generate captions
    caption_sections = generate_weekend_caption(events)
    if any(caption_sections.values()):
        sections = {
            "INSTAGRAM": caption_sections["instagram"],
            "FACEBOOK": caption_sections["facebook"],
            "SHORT (Blog/Email)": caption_sections["short"],
        }
        caption_path = _write_caption_file(week_dir / "captions.txt", sections)
        outputs.append(caption_path)

    return outputs


def generate_monthly_images(
    events: list[dict],
    year: int,
    month: int,
    formats: list[str],
) -> list[Path]:
    """Generate monthly calendar images. Returns list of output paths."""
    month_name = date(year, month, 1).strftime("%B %Y")
    month_dir = OUTPUT_DIR / f"Monthly Calendar {month_name}"
    outputs = []

    for fmt in formats:
        template = MonthlyCalendarTemplate(fmt)
        template.render(events=events, year=year, month=month)
        path = month_dir / f"monthly_calendar_{fmt}.png"
        template.save(path)
        outputs.append(path)

    return outputs


def main():
    parser = argparse.ArgumentParser(description="Generate social media images for PCSS races")
    parser.add_argument("--type", choices=TEMPLATE_TYPES, help="Only generate this template type")
    parser.add_argument("--format", choices=list(FORMATS.keys()), help="Only generate this format")
    parser.add_argument("--event", help="Specific event ID (e.g., imd-14398)")
    parser.add_argument("--month", help="Month for monthly_calendar (YYYY-MM, default: current month)")
    parser.add_argument("--preview", action="store_true", help="Open first image after generation")
    parser.add_argument("--all-events", action="store_true", help="Include non-PCSS events too")
    parser.add_argument("--captions-only", action="store_true", help="Generate captions without images (fast, no Pillow needed)")
    args = parser.parse_args()

    types = [args.type] if args.type else ["pre_race", "race_day"]
    formats = [args.format] if args.format else list(FORMATS.keys())

    events = load_events()
    all_outputs = []

    # Monthly calendar — standalone flow
    if args.type == "monthly_calendar":
        if args.month:
            try:
                parts = args.month.split("-")
                year, month = int(parts[0]), int(parts[1])
            except (ValueError, IndexError):
                print(f"Invalid --month format: {args.month} (expected YYYY-MM)")
                sys.exit(1)
        else:
            today = date.today()
            year, month = today.year, today.month

        print(f"Generating monthly calendar for {year}-{month:02d}")
        outputs = generate_monthly_images(events, year, month, formats)
        all_outputs.extend(outputs)

        print(f"\nGenerated {len(all_outputs)} image(s)")
        for p in all_outputs:
            print(f"  {p}")

        if args.preview and all_outputs:
            first = str(all_outputs[0])
            print(f"\nOpening: {first}")
            subprocess.run(["open", first])
        return

    if args.event:
        # Specific event
        matching = [e for e in events if e["id"] == args.event]
        if not matching:
            print(f"Event not found: {args.event}")
            sys.exit(1)
        event = matching[0]
        print(f"Generating for: {event['name']}")
        outputs = generate_event_images(event, types, formats, all_events=events, captions_only=args.captions_only)
        all_outputs.extend(outputs)
    else:
        # All upcoming PCSS events
        if args.all_events:
            upcoming = [
                e for e in events
                if e.get("dates", {}).get("end", "") >= date.today().isoformat()
            ]
        else:
            upcoming = filter_pcss_upcoming(events)

        if not upcoming:
            print("No upcoming PCSS events found.")
            sys.exit(0)

        print(f"Found {len(upcoming)} upcoming event(s)")

        # Generate per-event images
        event_types = [t for t in types if t not in ("weekly_preview", "weekend_preview")]
        if event_types:
            for event in upcoming:
                print(f"  Generating: {event['name']}")
                outputs = generate_event_images(event, event_types, formats, all_events=events, captions_only=args.captions_only)
                all_outputs.extend(outputs)

        # Generate weekly preview
        if "weekly_preview" in types or args.type is None:
            weekly_events = get_weekly_events(events)
            if weekly_events:
                print(f"  Generating weekly preview ({len(weekly_events)} events)")
                outputs = generate_weekly_images(weekly_events, formats, captions_only=args.captions_only)
                all_outputs.extend(outputs)
            else:
                print("  No PCSS events this week, skipping weekly preview")

        # Generate weekend preview
        if "weekend_preview" in types or args.type is None:
            weekend_events = get_weekend_events(events)
            if weekend_events:
                print(f"  Generating weekend preview ({len(weekend_events)} events)")
                outputs = generate_weekend_images(weekend_events, formats, captions_only=args.captions_only)
                all_outputs.extend(outputs)
            else:
                print("  No events this weekend, skipping weekend preview")

    label = "file(s)" if args.captions_only else "image(s)"
    print(f"\nGenerated {len(all_outputs)} {label}")
    for p in all_outputs:
        print(f"  {p}")

    if args.preview and all_outputs:
        first = str(all_outputs[0])
        print(f"\nOpening: {first}")
        subprocess.run(["open", first])


if __name__ == "__main__":
    main()
