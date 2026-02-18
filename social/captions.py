"""Caption generation for social media posts.

Generates copy-pasteable captions for Instagram, Facebook, and blog/email
alongside social images, so posting takes under a minute per event.
"""

from __future__ import annotations

import re
from pathlib import Path


def _event_title(event: dict) -> str:
    """Extract a clean title from an event name.

    Event names follow patterns like:
        "South Series- 2 GS- Snowbird"
        "WR Devo / NJR - 2SL/2GS- Mission Ridge"
    We strip the discipline and venue suffixes to get just the title.
    """
    name = event.get("name", "")
    # Split on " - " or "- " patterns; the first segment is the title
    parts = re.split(r'\s*-\s*', name)
    return parts[0].strip() if parts else name


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_disciplines(event: dict) -> str:
    """Format discipline counts into a readable string.

    Examples:
        {"SL": 1, "GS": 2} → "1x SL, 2x GS"
        {"GS": 1}          → "GS"
        {}                  → ""
    """
    counts = event.get("discipline_counts", {})
    if not counts:
        return ""
    parts = []
    for disc, count in counts.items():
        if count > 1:
            parts.append(f"{count}x {disc}")
        else:
            parts.append(disc)
    return ", ".join(parts)


def _venue_hashtag(venue: str) -> str:
    """Convert a venue name to a hashtag.

    Examples:
        "Utah Olympic Park" → "#UtahOlympicPark"
        "Snowbird"          → "#Snowbird"
        "Mt. Bachelor"      → "#MtBachelor"
    """
    if not venue or venue == "TBD":
        return ""
    # Remove dots/punctuation, then title-case and join
    cleaned = re.sub(r'[.\-/]', ' ', venue)
    words = cleaned.split()
    tag = "".join(w.capitalize() for w in words)
    return f"#{tag}"


def _write_caption_file(path: Path, sections: dict[str, str]) -> Path:
    """Write a multi-section caption file.

    sections: dict with keys like 'instagram', 'facebook', 'short'
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for label, content in sections.items():
        lines.append(f"=== {label.upper()} ===")
        lines.append(content.strip())
        lines.append("")
    path.write_text("\n".join(lines).rstrip() + "\n")
    return path


# ---------------------------------------------------------------------------
# Event captions
# ---------------------------------------------------------------------------

def _find_historical_recap(event: dict, all_events: list[dict]) -> str | None:
    """Check if any completed event at the same venue has a blog recap."""
    venue = event.get("venue", "")
    if not venue or venue == "TBD":
        return None
    for e in all_events:
        if (
            e.get("id") != event.get("id")
            and e.get("venue") == venue
            and e.get("status") == "completed"
            and e.get("blog_recap_urls")
        ):
            return venue
    return None


def generate_event_captions(event: dict, all_events: list[dict] | None = None) -> dict:
    """Generate pre_race, race_day, and blog_intro captions for an event.

    Returns dict with keys: pre_race, race_day, blog_intro
    """
    all_events = all_events or []

    title = _event_title(event)
    venue = event.get("venue", "")
    state = event.get("state", "")
    dates_display = event.get("dates", {}).get("display", "")
    disciplines = _format_disciplines(event)
    age_groups = ", ".join(event.get("age_groups", []))
    circuit = event.get("circuit", "")

    # Location string
    location = venue
    if state:
        location = f"{venue}, {state}" if venue else state

    # Discipline line
    disc_line = f" featuring {disciplines}" if disciplines else ""

    # Age group line
    age_line = f" for {age_groups} athletes" if age_groups else ""

    # Hashtags
    tags = []
    if circuit:
        tags.append(f"#{circuit.replace(' ', '')}Alpine")
    tags.append("#YouthSkiRacing")
    venue_tag = _venue_hashtag(venue)
    if venue_tag:
        tags.append(venue_tag)
    tags.append("#PCSkiRacing")
    hashtag_str = " ".join(tags)

    # Historical context
    recap_venue = _find_historical_recap(event, all_events)
    recap_line = ""
    if recap_venue:
        recap_line = f"\n\nCheck out our recap from the last race at {recap_venue}!"

    # --- Pre-race ---
    pre_race_ig = (
        f"This weekend: {title} at {location} ({dates_display}).{disc_line}{age_line}.{recap_line}"
        f"\n\n{hashtag_str}"
    )

    pre_race_fb = (
        f"Coming up: {title} takes place at {location}, {dates_display}.{disc_line}{age_line}."
        f"{recap_line}"
        f"\n\nGood luck to all athletes competing!"
    )

    pre_race_short = (
        f"{title} at {location} ({dates_display}){disc_line}{age_line}."
    )

    # --- Race day ---
    race_day_ig = (
        f"It's race day! {title} is underway at {location}. "
        f"Good luck to all athletes!"
        f"\n\n#RaceDay {hashtag_str}"
    )

    race_day_fb = (
        f"It's race day! {title} is underway at {location}. "
        f"Good luck to all athletes competing today!"
    )

    race_day_short = (
        f"Race day: {title} at {location}."
    )

    # --- Blog intro ---
    blog_intro = pre_race_short

    return {
        "pre_race": {
            "instagram": pre_race_ig,
            "facebook": pre_race_fb,
            "short": pre_race_short,
        },
        "race_day": {
            "instagram": race_day_ig,
            "facebook": race_day_fb,
            "short": race_day_short,
        },
        "blog_intro": blog_intro,
    }


# ---------------------------------------------------------------------------
# Weekly / Weekend captions
# ---------------------------------------------------------------------------

def _summarize_events(events: list[dict]) -> str:
    """Build a comma-separated summary of events for multi-event captions."""
    parts = []
    for e in events:
        title = _event_title(e)
        venue = e.get("venue", "")
        dates_display = e.get("dates", {}).get("display", "")
        # Compact date: strip year
        compact_date = re.sub(r',?\s*\d{4}$', '', dates_display).strip()
        if venue:
            parts.append(f"{title} at {venue} ({compact_date})")
        else:
            parts.append(f"{title} ({compact_date})")
    return ", ".join(parts)


def generate_weekly_caption(events: list[dict]) -> dict[str, str]:
    """Generate a weekly preview caption summarizing the week's events.

    Returns dict with keys: instagram, facebook, short
    """
    if not events:
        return {"instagram": "", "facebook": "", "short": ""}

    summary = _summarize_events(events)
    count = len(events)
    event_word = "event" if count == 1 else "events"

    instagram = (
        f"This week in PC ski racing: {summary}."
        f"\n\n#PCSkiRacing #IMDAlpine #YouthSkiRacing"
    )

    facebook = (
        f"This week in PC ski racing: {summary}."
        f"\n\nGood luck to all athletes competing this week!"
    )

    short = f"This week in PC ski racing: {summary}."

    return {"instagram": instagram, "facebook": facebook, "short": short}


def generate_weekend_caption(events: list[dict]) -> dict[str, str]:
    """Generate a weekend preview caption summarizing weekend events.

    Returns dict with keys: instagram, facebook, short
    """
    if not events:
        return {"instagram": "", "facebook": "", "short": ""}

    summary = _summarize_events(events)

    instagram = (
        f"This weekend in PC ski racing: {summary}."
        f"\n\n#PCSkiRacing #IMDAlpine #YouthSkiRacing #WeekendRacing"
    )

    facebook = (
        f"This weekend in PC ski racing: {summary}."
        f"\n\nGood luck to all athletes racing this weekend!"
    )

    short = f"This weekend in PC ski racing: {summary}."

    return {"instagram": instagram, "facebook": facebook, "short": short}
