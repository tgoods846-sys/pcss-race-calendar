"""Parse IMD iCal SUMMARY strings into structured race data.

The SUMMARY field packs event name, disciplines, and venue into a single
dash-separated string with several format variations:

  Standard:    "South Series- 2 GS- Snowbird"
  No counts:   "IMD Finals- SL/GS- Park City"
  No-space:    "WR Devo FIS-Sun Valley"
  Canceled:    "U16 ... Qualifier- 3 SG- Bogus Basin-Canceled"
  Dual venue:  "WR Elite- 2 SL/2 GS- Snowbird/Utah Olympic Park"
  Disc in name:"YSL Kombi- Utah Olympic Park"
"""

from ingestion.config import (
    CANCELED_SUFFIX_PATTERN,
    DISCIPLINE_NORMALIZE,
    DISCIPLINE_PATTERN,
    KNOWN_VENUES,
    VENUE_NORMALIZE,
)


def parse_summary(summary: str) -> dict:
    """Parse a SUMMARY string into structured components.

    Returns dict with keys:
        event_name: str
        disciplines: list[str]  — normalized codes like ["SL", "GS"]
        discipline_counts: dict[str, int]  — e.g. {"SL": 2, "GS": 2}
        venue: str
        canceled: bool
    """
    text = summary.strip()

    # Step 1: Detect and strip canceled/postponed suffix
    canceled = False
    m = CANCELED_SUFFIX_PATTERN.search(text)
    if m:
        canceled = True
        text = text[: m.start()].rstrip()

    # Step 2: Split on "- " (dash-space)
    segments = text.split("- ")
    segments = [s.strip() for s in segments if s.strip()]

    if len(segments) >= 3:
        return _parse_three_plus(segments, canceled)
    elif len(segments) == 2:
        return _parse_two(segments, canceled)
    else:
        return _parse_one(segments[0] if segments else text, canceled)


def _parse_three_plus(segments: list, canceled: bool) -> dict:
    """Handle: "Event Name- Disciplines- Venue" (and extra segments)."""
    event_name = segments[0]
    # Venue is always the last segment
    venue_raw = segments[-1]
    # Disciplines are all middle segments joined
    disc_raw = "- ".join(segments[1:-1])

    disciplines, counts = _extract_disciplines(disc_raw)
    venue = _normalize_venue(venue_raw)

    return {
        "event_name": event_name,
        "disciplines": disciplines,
        "discipline_counts": counts,
        "venue": venue,
        "canceled": canceled,
    }


def _parse_two(segments: list, canceled: bool) -> dict:
    """Handle: "Event Name- Venue" or "Event Name- Disciplines"."""
    event_name = segments[0]
    second = segments[1]

    # Check if the second segment is a known venue
    if _is_venue(second):
        # "YSL Kombi- Utah Olympic Park" — discipline might be in the name
        disciplines, counts = _extract_disciplines(event_name)
        venue = _normalize_venue(second)
        return {
            "event_name": event_name,
            "disciplines": disciplines,
            "discipline_counts": counts,
            "venue": venue,
            "canceled": canceled,
        }

    # Check if second segment has disciplines
    disciplines, counts = _extract_disciplines(second)
    if disciplines:
        # "Event Name- Disciplines" with no venue (unusual)
        return {
            "event_name": event_name,
            "disciplines": disciplines,
            "discipline_counts": counts,
            "venue": "",
            "canceled": canceled,
        }

    # Default: treat second segment as venue
    venue = _normalize_venue(second)
    return {
        "event_name": event_name,
        "disciplines": [],
        "discipline_counts": {},
        "venue": venue,
        "canceled": canceled,
    }


def _parse_one(text: str, canceled: bool) -> dict:
    """Handle no-space-dash formats: "WR Devo FIS-Sun Valley"."""
    # Try splitting on plain "-" and check if any part is a known venue
    parts = text.split("-")
    if len(parts) >= 2:
        # Try from the right — the venue is most likely the last part
        for i in range(len(parts) - 1, 0, -1):
            candidate_venue = parts[i].strip()
            normalized = _normalize_venue(candidate_venue)
            if _is_venue(normalized) or _is_venue(candidate_venue):
                event_name = "-".join(parts[:i]).strip()
                disciplines, counts = _extract_disciplines(event_name)
                return {
                    "event_name": event_name,
                    "disciplines": disciplines,
                    "discipline_counts": counts,
                    "venue": normalized,
                    "canceled": canceled,
                }

    # Fallback: entire string is the event name
    return {
        "event_name": text,
        "disciplines": [],
        "discipline_counts": {},
        "venue": "",
        "canceled": canceled,
    }


def _extract_disciplines(text: str) -> tuple:
    """Extract discipline codes and counts from a text segment.

    Returns (disciplines: list[str], counts: dict[str, int]).
    """
    disciplines = []
    counts = {}

    # Split on "/" to handle "2 SL/2 GS/2 SG" or "SL/GS"
    parts = text.split("/")
    for part in parts:
        part = part.strip()
        match = DISCIPLINE_PATTERN.search(part)
        if match:
            count_str = match.group(1)
            disc_raw = match.group(2)
            disc = DISCIPLINE_NORMALIZE.get(disc_raw.lower(), disc_raw.upper())
            count = int(count_str.strip()) if count_str else 1
            if disc not in disciplines:
                disciplines.append(disc)
            counts[disc] = count

    return disciplines, counts


def _is_venue(text: str) -> bool:
    """Check if text matches a known venue name."""
    normalized = _normalize_venue(text)
    for venue in KNOWN_VENUES:
        if venue.lower() == normalized.lower():
            return True
    return False


def _normalize_venue(venue: str) -> str:
    """Normalize venue typos and variants."""
    venue = venue.strip()
    # Check direct normalization map
    if venue in VENUE_NORMALIZE:
        return VENUE_NORMALIZE[venue]
    # Check case-insensitive
    for typo, correct in VENUE_NORMALIZE.items():
        if venue.lower() == typo.lower():
            return correct
    return venue
