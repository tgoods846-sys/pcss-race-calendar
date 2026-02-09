"""Refresh the race database from all sources.

Fetches IMD iCal feed, merges USSA manual seeds, applies age group
extraction, circuit mapping, PCSS tagging, and writes race_database.json.

Preserves manual overrides (blog links, custom tags) from existing database.

Usage: python3 -m ingestion.refresh
"""

import json
import re
from datetime import date, datetime

from ingestion.config import (
    CANCELED_SUFFIX_PATTERN,
    DATA_DIR,
    RACE_DATABASE_PATH,
    BLOG_LINKS_PATH,
    VENUE_STATE_MAP,
)
from ingestion.ical_parser import fetch_and_parse
from ingestion.age_group_extractor import extract_age_groups
from ingestion.circuit_mapper import map_circuit
from ingestion.pcss_tagger import is_pcss_relevant
from ingestion.pdf_age_extractor import enrich_events_with_pdf_ages
from ingestion.ussa_seeds import load_ussa_seeds


# Descriptions matching these patterns are generic IMD labels, not useful scheduling info
_JUNK_DESCRIPTION_PATTERNS = [
    re.compile(r"^\s*Team Assignments?\s*[-–]?\s*\w*\s*$", re.IGNORECASE),
    re.compile(r"^\s*Attendee List\s*$", re.IGNORECASE),
    re.compile(r"RACE ANNOUNCEMENT PDF", re.IGNORECASE),
]


def _clean_description(desc: str) -> str:
    """Filter out generic/unhelpful IMD description text.

    Keep descriptions with actual scheduling info (gender splits, race order).
    Remove generic labels like 'Team Assignments', 'Attendee List', or
    lines that just reference RACE ANNOUNCEMENT PDFs.
    """
    if not desc or not desc.strip():
        return ""

    # Filter out lines that are just PDF links or generic labels
    lines = desc.strip().split("\n")
    useful_lines = []
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
        is_junk = any(p.search(line_stripped) for p in _JUNK_DESCRIPTION_PATTERNS)
        if not is_junk:
            useful_lines.append(line_stripped)

    return "\n".join(useful_lines)


def _clean_summary_for_display(summary_raw: str) -> str:
    """Strip canceled/postponed suffix from raw SUMMARY for display."""
    text = summary_raw.strip()
    m = CANCELED_SUFFIX_PATTERN.search(text)
    if m:
        text = text[:m.start()].rstrip()
    return text


def _format_date_display(start_str: str, end_str: str) -> str:
    """Format dates for display: 'Feb 9-10, 2026' or 'Feb 9, 2026'."""
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)

    months = [
        "Jan", "Feb", "Mar", "Apr", "May", "Jun",
        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ]

    if start == end:
        return f"{months[start.month - 1]} {start.day}, {start.year}"

    if start.month == end.month and start.year == end.year:
        return f"{months[start.month - 1]} {start.day}\u2013{end.day}, {start.year}"

    if start.year == end.year:
        return (
            f"{months[start.month - 1]} {start.day}\u2013"
            f"{months[end.month - 1]} {end.day}, {start.year}"
        )

    return (
        f"{months[start.month - 1]} {start.day}, {start.year}\u2013"
        f"{months[end.month - 1]} {end.day}, {end.year}"
    )


def _compute_status(start_str: str, end_str: str) -> str:
    """Compute event status based on today's date."""
    today = date.today()
    start = date.fromisoformat(start_str)
    end = date.fromisoformat(end_str)

    if today < start:
        return "upcoming"
    elif today > end:
        return "completed"
    else:
        return "in_progress"


def _lookup_state(venue: str) -> str:
    """Look up state abbreviation for a venue."""
    # Direct match
    if venue in VENUE_STATE_MAP:
        return VENUE_STATE_MAP[venue]

    # Check if any known venue is a substring (for dual venues like "Snowbird/UOP")
    for known_venue, state in VENUE_STATE_MAP.items():
        if known_venue.lower() in venue.lower():
            return state

    return ""


def _make_id(uid: str, source_type: str) -> str:
    """Generate a stable ID from the iCal UID."""
    if source_type == "ussa_manual":
        return uid  # USSA seeds already have IDs

    # Extract numeric event ID from UID like "14421-1770595200-1770767999@imdalpine.org"
    match = re.match(r"(\d+)", uid)
    if match:
        return f"imd-{match.group(1)}"
    return f"imd-{uid[:20]}"


def _load_existing_overrides() -> dict:
    """Load manual overrides from existing race database."""
    overrides = {}
    if RACE_DATABASE_PATH.exists():
        with open(RACE_DATABASE_PATH) as f:
            data = json.load(f)
            for event in data.get("events", []):
                eid = event.get("id", "")
                if eid:
                    overrides[eid] = {
                        "blog_recap_url": event.get("blog_recap_url"),
                        "results_url": event.get("results_url"),
                        "pcss_relevant_override": event.get("pcss_relevant_override"),
                    }
    return overrides


def _load_blog_links() -> dict:
    """Load manual blog link mappings."""
    if BLOG_LINKS_PATH.exists():
        with open(BLOG_LINKS_PATH) as f:
            return json.load(f)
    return {}


def refresh():
    """Main refresh pipeline."""
    print("Fetching IMD iCal feed...")
    imd_events = fetch_and_parse()
    print(f"  Parsed {len(imd_events)} events from IMD feed")

    print("Loading USSA manual seeds...")
    ussa_events = load_ussa_seeds()
    print(f"  Loaded {len(ussa_events)} USSA events")

    # Load existing overrides and blog links
    overrides = _load_existing_overrides()
    blog_links = _load_blog_links()

    # Process IMD events into final schema
    all_events = []
    seen_ids = set()

    for raw in imd_events:
        event_id = _make_id(raw["uid"], "imd_ical")
        if event_id in seen_ids:
            continue
        seen_ids.add(event_id)

        age_groups = extract_age_groups(raw["event_name"], raw["categories"])
        circuit, series = map_circuit(raw["categories"], raw["event_name"])
        state = _lookup_state(raw["venue"])
        status = (
            "canceled" if raw["canceled"]
            else _compute_status(raw["start_date"], raw["end_date"])
        )

        # Use full IMD SUMMARY (minus canceled suffix) as the display name
        display_name = _clean_summary_for_display(raw["summary_raw"])

        event = {
            "id": event_id,
            "name": display_name,
            "dates": {
                "start": raw["start_date"],
                "end": raw["end_date"],
                "display": _format_date_display(raw["start_date"], raw["end_date"]),
            },
            "venue": raw["venue"],
            "state": state,
            "disciplines": raw["disciplines"],
            "discipline_counts": raw["discipline_counts"],
            "circuit": circuit,
            "series": series,
            "age_groups": age_groups,
            "status": status,
            "pcss_relevant": is_pcss_relevant(raw),
            "td_name": raw["td_name"],
            "description": _clean_description(raw["description"]),
            "source_url": raw["source_url"],
            "source_type": "imd_ical",
            "blog_recap_url": None,
            "results_url": None,
        }

        # Apply overrides from existing database
        if event_id in overrides:
            ovr = overrides[event_id]
            if ovr.get("blog_recap_url"):
                event["blog_recap_url"] = ovr["blog_recap_url"]
            if ovr.get("results_url"):
                event["results_url"] = ovr["results_url"]
            if ovr.get("pcss_relevant_override") is not None:
                event["pcss_relevant"] = ovr["pcss_relevant_override"]

        # Apply blog links
        if event_id in blog_links:
            event["blog_recap_url"] = blog_links[event_id]

        all_events.append(event)

    # Add USSA seeds (skip duplicates by matching on name+dates)
    imd_keys = {(e["name"], e["dates"]["start"]) for e in all_events}
    for seed in ussa_events:
        seed_key = (seed["name"], seed["dates"]["start"])
        if seed_key in imd_keys:
            # IMD already has this event (e.g., WR events appear in IMD feed too)
            continue
        if seed["id"] in seen_ids:
            continue
        seen_ids.add(seed["id"])

        # Compute status for USSA seeds
        status = _compute_status(seed["dates"]["start"], seed["dates"]["end"])
        seed["dates"]["display"] = _format_date_display(
            seed["dates"]["start"], seed["dates"]["end"]
        )
        seed["status"] = status
        seed["pcss_relevant"] = False
        seed["td_name"] = seed.get("td_name", "")
        seed["blog_recap_url"] = seed.get("blog_recap_url")
        seed["results_url"] = seed.get("results_url")

        # Apply overrides
        if seed["id"] in overrides:
            ovr = overrides[seed["id"]]
            if ovr.get("blog_recap_url"):
                seed["blog_recap_url"] = ovr["blog_recap_url"]
            if ovr.get("results_url"):
                seed["results_url"] = ovr["results_url"]

        all_events.append(seed)

    # Enrich with age group data from Race Announcement PDFs
    print("\nExtracting age groups from Race Announcement PDFs...")
    pdf_ages = enrich_events_with_pdf_ages(all_events)
    enriched_count = 0
    for event in all_events:
        eid = event.get("id", "")
        if eid in pdf_ages:
            pdf_found = pdf_ages[eid]
            existing = event.get("age_groups", [])
            # Merge: PDF data supplements iCal data
            merged = sorted(
                set(existing) | set(pdf_found),
                key=lambda x: int(x[1:]),
            )
            if merged != existing:
                event["age_groups"] = merged
                enriched_count += 1
    print(f"  Enriched {enriched_count} events with PDF age data")

    # Sort by start date
    all_events.sort(key=lambda e: e["dates"]["start"])

    # Build output
    database = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "source": "IMD iCal + USSA manual",
        "event_count": len(all_events),
        "events": all_events,
    }

    # Write output
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with open(RACE_DATABASE_PATH, "w") as f:
        json.dump(database, f, indent=2, ensure_ascii=False)

    print(f"\nWrote {len(all_events)} events to {RACE_DATABASE_PATH}")

    # Print summary
    pcss_count = sum(1 for e in all_events if e["pcss_relevant"])
    circuits = {}
    for e in all_events:
        circuits[e["circuit"]] = circuits.get(e["circuit"], 0) + 1

    print(f"  PCSS-relevant: {pcss_count}")
    print(f"  By circuit: {circuits}")
    statuses = {}
    for e in all_events:
        statuses[e["status"]] = statuses.get(e["status"], 0) + 1
    print(f"  By status: {statuses}")


if __name__ == "__main__":
    refresh()
