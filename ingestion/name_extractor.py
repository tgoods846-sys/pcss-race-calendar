"""Extract racer names from IMD race result PDFs.

Reuses the scraping logic from pcss_detector.py to find result PDFs
and match them to events. Downloads each PDF, extracts text, parses
racer names in IMD result format (Lastname, Firstname after bib + NAT code),
and builds a racer database mapping names to event IDs.

Usage (standalone): python3 -m ingestion.name_extractor
"""

from __future__ import annotations

import io
import json
import re
from datetime import datetime

import requests
from pypdf import PdfReader

from ingestion.config import (
    RACER_CACHE_PATH,
    RACER_DATABASE_PATH,
)
from ingestion.pcss_detector import (
    _scrape_results_page,
    _match_to_event,
)

# IMD result format: rank, bib, NAT code, then "Lastname, Firstname"
# Examples: "1  4 I6989553 Johnson, Feren" or "12  42 N6445585 O'Brien, Mary-Kate"
# Sometimes just bib + NAT code (no rank column)
_NAME_PATTERN = re.compile(
    r"^\s*\d{1,4}\s+"                          # rank or bib
    r"(?:\d{1,4}\s+)?"                         # optional second number (bib when rank is first)
    r"[A-Z]\d{5,10}\s+"                        # NAT code (e.g. I6989553)
    r"([A-Za-z][A-Za-z'\-]+)"                  # Lastname
    r",\s*"                                    # comma separator
    r"([A-Za-z][A-Za-z'\-]+)",                 # Firstname
    re.MULTILINE,
)

# Header/false-positive words to filter out (uppercase words that look like last names)
_HEADER_WORDS = frozenset({
    "OFFICIAL", "RESULTS", "SLALOM", "GIANT", "SUPER",
    "DOWNHILL", "COMBINED", "PARALLEL", "KOMBI", "ALPINE",
    "DISQUALIFIED", "NOT", "DID", "DNS", "DNF", "DSQ",
    "RACE", "JURY", "TECHNICAL", "COURSE", "WEATHER",
    "FORERUNNERS", "NUMBER", "PENALTY", "CALCULATION",
    "INTERNATIONAL", "FEDERATION", "INTERMOUNTAIN",
    "DIVISION", "NORTH", "SOUTH", "SERIES", "FINAL",
    "CHAMPIONSHIP", "CHAMPIONSHIPS", "QUALIFIER",
    "START", "FINISH", "TIME", "TOTAL", "DIFF",
    "RANK", "BIB", "NAME", "TEAM", "RUN", "STATE",
    "CLUB", "CLASS", "SEED", "POINTS",
})


def _is_valid_name(last: str, first: str) -> bool:
    """Check if an extracted name is a real person name (not a header word)."""
    if last.upper() in _HEADER_WORDS or first.upper() in _HEADER_WORDS:
        return False
    if len(last) < 2 or len(first) < 2:
        return False
    # All digits shouldn't happen but guard against it
    if last.isdigit() or first.isdigit():
        return False
    return True


def _normalize_name(last: str, first: str) -> str:
    """Normalize to 'Firstname Lastname' display format."""
    # Handle names like O'BRIEN -> O'Brien, MC'DONALD -> Mc'Donald
    def title_part(s):
        # Handle apostrophes and hyphens
        parts = re.split(r"(['\-])", s)
        return "".join(
            p.capitalize() if p not in ("'", "-") else p
            for p in parts
        )
    return f"{title_part(first)} {title_part(last)}"


def parse_names_from_text(text: str) -> list[tuple[str, str]]:
    """Parse racer names from PDF text.

    Returns list of (display_name, key) tuples.
    """
    seen = set()
    names = []

    for m in _NAME_PATTERN.finditer(text):
        last_raw = m.group(1)
        first_raw = m.group(2)

        if not _is_valid_name(last_raw, first_raw):
            continue

        display = _normalize_name(last_raw, first_raw)
        key = display.lower()

        if key not in seen:
            seen.add(key)
            names.append((display, key))

    return names


def _extract_names_from_pdf(pdf_url: str) -> list[tuple[str, str]]:
    """Download a PDF and extract racer names."""
    try:
        resp = requests.get(pdf_url, timeout=15)
        resp.raise_for_status()
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

    return parse_names_from_text(text)


def _load_cache() -> dict:
    """Load the racer names cache."""
    if RACER_CACHE_PATH.exists():
        with open(RACER_CACHE_PATH) as f:
            return json.load(f)
    return {"last_checked": None, "pdf_names": {}}


def _save_cache(cache: dict):
    """Save the racer names cache."""
    cache["last_checked"] = datetime.now().isoformat(timespec="seconds")
    with open(RACER_CACHE_PATH, "w") as f:
        json.dump(cache, f, indent=2)


def extract_racer_names(events: list) -> dict:
    """Extract racer names from race result PDFs and build a racer database.

    Args:
        events: list of event dicts from the database

    Returns:
        dict with racer database structure ready for JSON output
    """
    print("\nExtracting racer names from race result PDFs...")

    groups = _scrape_results_page()
    if not groups:
        print("  No result groups found on results page")
        return {"generated_at": "", "racer_count": 0, "racers": []}

    print(f"  Found {len(groups)} result groups on IMD results page")

    cache = _load_cache()
    pdf_names_cache = cache.get("pdf_names", {})
    pdfs_downloaded = 0

    # Map: key -> {name, event_ids set}
    racer_map: dict[str, dict] = {}

    for group in groups:
        event_id = _match_to_event(group, events)
        if not event_id:
            continue

        for pdf_url in group["pdf_urls"]:
            # Check cache first
            if pdf_url in pdf_names_cache:
                names = [
                    (entry["display"], entry["key"])
                    for entry in pdf_names_cache[pdf_url]
                ]
            else:
                # Download and extract
                pdfs_downloaded += 1
                names = _extract_names_from_pdf(pdf_url)
                pdf_names_cache[pdf_url] = [
                    {"display": d, "key": k} for d, k in names
                ]

            # Add names to racer map
            for display, key in names:
                if key not in racer_map:
                    racer_map[key] = {"name": display, "event_ids": set()}
                racer_map[key]["event_ids"].add(event_id)

    # Save updated cache
    cache["pdf_names"] = pdf_names_cache
    _save_cache(cache)

    # Build output
    racers = sorted(
        [
            {
                "name": info["name"],
                "key": key,
                "event_ids": sorted(info["event_ids"]),
            }
            for key, info in racer_map.items()
        ],
        key=lambda r: r["key"],
    )

    print(f"  Downloaded {pdfs_downloaded} new PDFs")
    print(f"  Found {len(racers)} unique racers across {len(racer_map)} entries")

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "racer_count": len(racers),
        "racers": racers,
    }


if __name__ == "__main__":
    # Standalone test: load database and run extraction
    from ingestion.config import RACE_DATABASE_PATH as DB_PATH

    with open(DB_PATH) as f:
        db = json.load(f)

    result = extract_racer_names(db["events"])
    print(f"\nExtracted {result['racer_count']} racers")

    # Write output
    with open(RACER_DATABASE_PATH, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {RACER_DATABASE_PATH}")

    # Show sample
    for racer in result["racers"][:20]:
        print(f"  {racer['name']} -> {len(racer['event_ids'])} events")
