"""Detect PCSS athlete participation from IMD race result PDFs.

Scrapes the IMD race results page, matches result groups to events
in our database by venue + date overlap, downloads PDFs and searches
for PCSS patterns to auto-set pcss_confirmed = True.

Usage (standalone): python3 -m ingestion.pcss_detector
"""

from __future__ import annotations

import io
import json
import re
from datetime import date, datetime

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ingestion.config import (
    IMD_RESULTS_URL,
    KNOWN_VENUES,
    PCSS_PATTERNS,
    PCSS_RESULTS_CACHE_PATH,
    VENUE_NORMALIZE,
)

# Month abbreviations used on the IMD results page
_MONTH_MAP = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4,
    "may": 5, "jun": 6, "jul": 7, "aug": 8,
    "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Pattern: "Dec. 20-23, 2025" or "Jan. 3-5, 2026" or "Mar. 14, 2025"
_DATE_RANGE_PATTERN = re.compile(
    r"(\w{3})\.?\s+(\d{1,2})(?:\s*-\s*(\d{1,2}))?,\s*(\d{4})"
)

def _parse_venue(header_text: str) -> str:
    """Extract venue name from a results header like '... @ Snowking, 2SL/2GS- Dec...'"""
    at_idx = header_text.find("@")
    if at_idx < 0:
        return ""

    after_at = header_text[at_idx + 1:].strip()

    # Stop at first comma or dash followed by discipline/date indicators
    # Split on comma or " -" / "- " to get the venue portion
    venue = re.split(r"[,\-]", after_at, maxsplit=1)[0].strip()

    # Normalize known typos
    venue = VENUE_NORMALIZE.get(venue, venue)
    return venue


def _parse_dates(header_text: str) -> tuple:
    """Extract (start_date, end_date) from header text.

    Returns (date, date) or (None, None) if unparseable.
    """
    m = _DATE_RANGE_PATTERN.search(header_text)
    if not m:
        return None, None

    month_str = m.group(1).lower().rstrip(".")
    day_start = int(m.group(2))
    day_end = int(m.group(3)) if m.group(3) else day_start
    year = int(m.group(4))

    month = _MONTH_MAP.get(month_str)
    if not month:
        return None, None

    try:
        return date(year, month, day_start), date(year, month, day_end)
    except ValueError:
        return None, None


def _scrape_results_page(url: str = None) -> list:
    """Scrape the IMD race results page for event groups.

    Returns list of dicts: {text, venue, date_start, date_end, pdf_urls}
    """
    url = url or IMD_RESULTS_URL
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: Could not fetch results page: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    groups = []

    # Find all <strong> tags — these are event headers
    for strong in soup.find_all("strong"):
        header_text = strong.get_text(strip=True)
        if not header_text or "@" not in header_text:
            continue

        venue = _parse_venue(header_text)
        date_start, date_end = _parse_dates(header_text)
        if not venue or not date_start:
            continue

        # Collect PDF links that follow this <strong> tag
        # They're siblings within the same <p> tag
        pdf_urls = []
        parent = strong.parent
        if parent:
            for a in parent.find_all("a", href=True):
                href = a["href"].strip()
                if href.lower().endswith(".pdf"):
                    pdf_urls.append(href)

        if not pdf_urls:
            continue

        groups.append({
            "text": header_text,
            "venue": venue,
            "date_start": date_start,
            "date_end": date_end,
            "pdf_urls": pdf_urls,
        })

    return groups


def _normalize_venue(venue: str) -> str:
    """Normalize a venue name for comparison."""
    return VENUE_NORMALIZE.get(venue, venue).lower().strip()


def _venues_match(results_venue: str, event_venue: str) -> bool:
    """Check if a results page venue matches an event venue.

    Uses case-insensitive substring matching against KNOWN_VENUES.
    """
    rv = _normalize_venue(results_venue)
    ev = _normalize_venue(event_venue)

    # Direct match
    if rv == ev:
        return True

    # Substring match (either direction)
    if rv in ev or ev in rv:
        return True

    return False


def _dates_overlap(rs: date, re_: date, es: date, ee: date, tolerance: int = 1) -> bool:
    """Check if two date ranges overlap, with tolerance for edge cases."""
    from datetime import timedelta
    rs_adj = rs - timedelta(days=tolerance)
    re_adj = re_ + timedelta(days=tolerance)
    return rs_adj <= ee and re_adj >= es


def _match_to_event(group: dict, events: list) -> str | None:
    """Match a results group to an event in our database.

    Returns event_id or None.
    """
    for event in events:
        event_venue = event.get("venue", "")
        event_start = date.fromisoformat(event["dates"]["start"])
        event_end = date.fromisoformat(event["dates"]["end"])

        if not _venues_match(group["venue"], event_venue):
            continue

        if _dates_overlap(group["date_start"], group["date_end"],
                          event_start, event_end):
            return event["id"]

    return None


def _check_pdf_for_pcss(pdf_url: str) -> bool:
    """Download a PDF and check if it contains PCSS patterns."""
    try:
        resp = requests.get(pdf_url, timeout=15)
        resp.raise_for_status()
        if not resp.content[:5].startswith(b"%PDF"):
            return False
        reader = PdfReader(io.BytesIO(resp.content))
    except Exception:
        return False

    text = ""
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        except Exception:
            continue

    if not text:
        return False

    return any(p.search(text) for p in PCSS_PATTERNS)


def _load_cache() -> dict:
    """Load the PCSS results cache."""
    if PCSS_RESULTS_CACHE_PATH.exists():
        with open(PCSS_RESULTS_CACHE_PATH) as f:
            return json.load(f)
    return {"last_checked": None, "checked_pdfs": {}}


def _save_cache(cache: dict):
    """Save the PCSS results cache."""
    cache["last_checked"] = datetime.now().isoformat(timespec="seconds")
    with open(PCSS_RESULTS_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def detect_pcss_confirmed(events: list) -> dict:
    """Detect which events have PCSS athletes in race results.

    Args:
        events: list of event dicts from the database

    Returns:
        dict mapping event_id -> True for confirmed events
    """
    print("\nChecking race results for PCSS participation...")

    groups = _scrape_results_page()
    if not groups:
        print("  No result groups found on results page")
        return {}

    print(f"  Found {len(groups)} result groups on IMD results page")

    cache = _load_cache()
    checked_pdfs = cache.get("checked_pdfs", {})
    confirmed = {}
    pdfs_downloaded = 0

    for group in groups:
        event_id = _match_to_event(group, events)
        if not event_id:
            continue

        # Check PDFs for this group
        pcss_found = False
        for pdf_url in group["pdf_urls"]:
            # Check cache first
            if pdf_url in checked_pdfs:
                if checked_pdfs[pdf_url].get("pcss_found"):
                    pcss_found = True
                continue

            # Download and check
            pdfs_downloaded += 1
            found = _check_pdf_for_pcss(pdf_url)
            checked_pdfs[pdf_url] = {
                "pcss_found": found,
                "checked_at": datetime.now().isoformat(timespec="seconds"),
            }

            if found:
                pcss_found = True
                # No need to check more PDFs for this group
                break

        if pcss_found:
            confirmed[event_id] = True

    # Save updated cache
    cache["checked_pdfs"] = checked_pdfs
    _save_cache(cache)

    print(f"  Downloaded {pdfs_downloaded} new PDFs")
    print(f"  PCSS confirmed: {len(confirmed)} events")

    return confirmed


if __name__ == "__main__":
    # Standalone test: load database and run detection
    from ingestion.config import RACE_DATABASE_PATH

    with open(RACE_DATABASE_PATH) as f:
        db = json.load(f)

    confirmed = detect_pcss_confirmed(db["events"])
    for eid in confirmed:
        print(f"  -> {eid}")
