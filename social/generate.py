"""CLI entry point for social image generation.

Usage:
    python3 -m social.generate                     # All upcoming PCSS events
    python3 -m social.generate --type pre_race     # Only pre-race images
    python3 -m social.generate --format post        # Only Instagram post format
    python3 -m social.generate --event imd-14398   # Specific event only
    python3 -m social.generate --preview           # Open first image after generation
"""

import argparse
import json
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

from social.config import FORMATS, OUTPUT_DIR, RACE_DB_PATH, TEMPLATE_TYPES
from social.templates.pre_race import PreRaceTemplate
from social.templates.race_day import RaceDayTemplate
from social.templates.weekly_preview import WeeklyPreviewTemplate


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


def generate_event_images(
    event: dict,
    types: list[str],
    formats: list[str],
) -> list[Path]:
    """Generate images for a single event. Returns list of output paths."""
    outputs = []
    event_dir = OUTPUT_DIR / event["id"]

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

    return outputs


def generate_weekly_images(
    events: list[dict],
    formats: list[str],
) -> list[Path]:
    """Generate weekly preview images. Returns list of output paths."""
    if not events:
        return []

    today = date.today()
    week_num = today.isocalendar()[1]
    week_dir = OUTPUT_DIR / "weekly" / f"{today.year}-W{week_num:02d}"
    outputs = []

    for fmt in formats:
        template = WeeklyPreviewTemplate(fmt)
        template.render(events=events)
        path = week_dir / f"weekly_preview_{fmt}.png"
        template.save(path)
        outputs.append(path)

    return outputs


def main():
    parser = argparse.ArgumentParser(description="Generate social media images for PCSS races")
    parser.add_argument("--type", choices=TEMPLATE_TYPES, help="Only generate this template type")
    parser.add_argument("--format", choices=list(FORMATS.keys()), help="Only generate this format")
    parser.add_argument("--event", help="Specific event ID (e.g., imd-14398)")
    parser.add_argument("--preview", action="store_true", help="Open first image after generation")
    parser.add_argument("--all-events", action="store_true", help="Include non-PCSS events too")
    args = parser.parse_args()

    types = [args.type] if args.type else ["pre_race", "race_day"]
    formats = [args.format] if args.format else list(FORMATS.keys())

    events = load_events()
    all_outputs = []

    if args.event:
        # Specific event
        matching = [e for e in events if e["id"] == args.event]
        if not matching:
            print(f"Event not found: {args.event}")
            sys.exit(1)
        event = matching[0]
        print(f"Generating for: {event['name']}")
        outputs = generate_event_images(event, types, formats)
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
        event_types = [t for t in types if t != "weekly_preview"]
        if event_types:
            for event in upcoming:
                print(f"  Generating: {event['name']}")
                outputs = generate_event_images(event, event_types, formats)
                all_outputs.extend(outputs)

        # Generate weekly preview
        if "weekly_preview" in types or args.type is None:
            weekly_events = get_weekly_events(events)
            if weekly_events:
                print(f"  Generating weekly preview ({len(weekly_events)} events)")
                outputs = generate_weekly_images(weekly_events, formats)
                all_outputs.extend(outputs)
            else:
                print("  No PCSS events this week, skipping weekly preview")

    print(f"\nGenerated {len(all_outputs)} image(s)")
    for p in all_outputs:
        print(f"  {p}")

    if args.preview and all_outputs:
        first = str(all_outputs[0])
        print(f"\nOpening: {first}")
        subprocess.run(["open", first])


if __name__ == "__main__":
    main()
