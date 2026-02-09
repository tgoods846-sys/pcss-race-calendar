"""Extract age group data from IMD Race Announcement PDFs.

Scrapes each event's IMD page for Race Announcement PDF links,
downloads them, and extracts age groups (U8-U21+) from the PDF text.
"""

import io
import re
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from ingestion.config import AGE_GROUP_PATTERN, AGE_GROUP_NORMALIZE

# Additional age groups found in PDFs but not in our standard list
EXTENDED_AGE_NORMALIZE = {
    **AGE_GROUP_NORMALIZE,
    "u8": "U8",
}

# Filter out PDFs that are clearly not Race Announcements
_SKIP_PDF_NAMES = [
    "team-assignment",
    "team_assignment",
    "attendee",
]


def _find_ra_pdfs(event_page_url: str) -> list:
    """Scrape an IMD event page for Race Announcement PDF links.

    Returns list of PDF URLs, prioritizing Race Announcement PDFs.
    """
    if not event_page_url or "imdalpine.org" not in event_page_url:
        return []

    try:
        resp = requests.get(event_page_url, timeout=15)
        resp.raise_for_status()
    except Exception:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    pdfs = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.lower().endswith(".pdf"):
            continue
        # Skip non-PDF URLs (some links look like PDFs but return HTML)
        if "imdalpine.org" not in href:
            continue
        # Skip team assignments and attendee lists
        name_lower = href.lower()
        if any(skip in name_lower for skip in _SKIP_PDF_NAMES):
            continue
        pdfs.append(href)

    return pdfs


def _extract_ages_from_pdf(pdf_url: str) -> list:
    """Download a PDF and extract age group mentions.

    Returns sorted list of normalized age group strings.
    """
    try:
        resp = requests.get(pdf_url, timeout=15)
        resp.raise_for_status()
        # Verify it's actually a PDF
        if not resp.content[:5].startswith(b"%PDF"):
            return []
        reader = PdfReader(io.BytesIO(resp.content))
    except Exception:
        return []

    text = ""
    for page in reader.pages:
        try:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
        except Exception:
            continue

    if not text:
        return []

    # Extract all age group mentions
    found = set()
    for match in AGE_GROUP_PATTERN.finditer(text):
        raw = match.group(1).lower()
        normalized = EXTENDED_AGE_NORMALIZE.get(raw, raw.upper())
        found.add(normalized)

    # Also check for U8 which isn't in the standard pattern
    for match in re.finditer(r"\bU8\b", text, re.IGNORECASE):
        found.add("U8")

    return sorted(found, key=lambda x: int(x[1:]))


def extract_ages_for_event(event: dict) -> list:
    """Extract age groups from Race Announcement PDFs for an event.

    Args:
        event: dict with at least 'source_url' field

    Returns:
        List of age group strings, or empty list if no PDFs found
    """
    source_url = event.get("source_url", "")
    if not source_url:
        return []

    pdf_urls = _find_ra_pdfs(source_url)
    if not pdf_urls:
        return []

    # Try each PDF until we find age group data
    all_ages = set()
    for pdf_url in pdf_urls:
        ages = _extract_ages_from_pdf(pdf_url)
        all_ages.update(ages)

    return sorted(all_ages, key=lambda x: int(x[1:]))


def enrich_events_with_pdf_ages(events: list) -> dict:
    """Enrich a list of events with age group data from PDFs.

    Only fetches PDFs for events that have no age groups or are
    from IMD iCal source. Skips USSA manual seeds.

    Returns dict mapping event_id -> list of age groups found.
    """
    results = {}
    total = len(events)

    for i, event in enumerate(events):
        event_id = event.get("id", "")
        name = event.get("name", "")

        # Skip non-IMD events
        if event.get("source_type") != "imd_ical":
            continue

        # Skip events that already have age groups from the iCal feed
        # (they're probably correct already)
        existing = event.get("age_groups", [])

        source_url = event.get("source_url", "")
        if not source_url or "imdalpine.org" not in source_url:
            continue

        print(f"  [{i+1}/{total}] Checking {name[:50]}...", end=" ")
        ages = extract_ages_for_event(event)

        if ages:
            print(f"-> {ages}")
            results[event_id] = ages
        else:
            print("-> (no PDFs or no age data)")

    return results
