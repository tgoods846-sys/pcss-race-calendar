"""Discover blog recap posts from the simsportsarena.com RSS feed and match
them to completed events in the race database.

Scrapes the RSS feed, extracts venue names from blog slugs, and matches
posts to events by venue + date proximity.

Usage (standalone): python3 -m ingestion.blog_linker
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta

import requests

from ingestion.config import (
    BLOG_LINKS_PATH,
    BLOG_RSS_URL,
    KNOWN_VENUES,
    VENUE_SLUG_ALIASES,
)


def _fetch_rss_items(url: str = None) -> list[dict]:
    """Fetch the RSS feed and return parsed items.

    Returns list of {title, link, slug, pub_date}.
    """
    url = url or BLOG_RSS_URL
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"  Warning: Could not fetch blog RSS feed: {e}")
        return []

    try:
        root = ET.fromstring(resp.text)
    except ET.ParseError as e:
        print(f"  Warning: Could not parse RSS XML: {e}")
        return []

    items = []
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pub_date_el = item.find("pubDate")

        if title_el is None or link_el is None:
            continue

        link = (link_el.text or "").strip()
        # Extract slug from URL: last path segment
        slug = link.rstrip("/").rsplit("/", 1)[-1] if link else ""

        pub_date = None
        if pub_date_el is not None and pub_date_el.text:
            try:
                # RSS dates: "Mon, 10 Feb 2026 00:00:00 GMT"
                dt = datetime.strptime(
                    pub_date_el.text.strip(), "%a, %d %b %Y %H:%M:%S %Z"
                )
                pub_date = dt.date()
            except ValueError:
                # Try ISO format as fallback
                try:
                    pub_date = date.fromisoformat(pub_date_el.text.strip()[:10])
                except ValueError:
                    pass

        items.append({
            "title": (title_el.text or "").strip(),
            "link": link,
            "slug": slug,
            "pub_date": pub_date,
        })

    return items


def _build_venue_slug_map() -> dict[str, str]:
    """Build a mapping from slug fragments to canonical venue names.

    Auto-generates from KNOWN_VENUES by slugifying each name, then merges
    in VENUE_SLUG_ALIASES for abbreviations.
    """
    slug_map: dict[str, str] = {}

    for venue in KNOWN_VENUES:
        # Slugify: lowercase, replace spaces/dots with hyphens, strip trailing hyphens
        slug = re.sub(r"[\s.]+", "-", venue.lower()).strip("-")
        slug_map[slug] = venue

        # Also add without hyphens for single-word matching
        # e.g. "snowbird" for "Snowbird", "brighton" for "Brighton"
        no_hyphen = slug.replace("-", "")
        if no_hyphen != slug:
            slug_map[no_hyphen] = venue

    # Merge explicit aliases (these override auto-generated ones)
    slug_map.update(VENUE_SLUG_ALIASES)

    return slug_map


def _extract_venue_from_slug(slug: str, slug_map: dict[str, str]) -> str | None:
    """Scan a blog slug for known venue fragments, longest match first.

    Returns the canonical venue name, or None if no venue found.
    """
    if not slug:
        return None

    slug_lower = slug.lower()

    # Sort candidate keys longest-first to prefer specific matches
    # e.g. "utah-olympic-park" before "park"
    candidates = sorted(slug_map.keys(), key=len, reverse=True)

    for fragment in candidates:
        # Check if fragment appears as a substring in the slug
        # Use word-boundary-like matching: fragment must be at start/end or
        # bordered by hyphens
        pattern = r"(?:^|-)" + re.escape(fragment) + r"(?:$|-)"
        if re.search(pattern, slug_lower):
            return slug_map[fragment]

    return None


def _match_blog_to_event(
    item: dict,
    events: list[dict],
    slug_map: dict[str, str],
    lookback_days: int = 14,
) -> tuple[str | None, str | None]:
    """Match a blog post to a completed event.

    Finds completed events matching the venue extracted from the blog slug,
    where the event end date is within lookback_days before the post pub_date.
    Prefers the most recent matching event.

    Returns (event_id, venue) or (None, None).
    """
    venue = _extract_venue_from_slug(item["slug"], slug_map)
    if not venue:
        return None, None

    pub_date = item.get("pub_date")
    if not pub_date:
        return None, None

    best_match = None
    best_end_date = None

    for event in events:
        # Only match completed events
        if event.get("status") not in ("completed", "in_progress"):
            continue

        event_venue = event.get("venue", "")
        # Check venue match (case-insensitive substring in either direction)
        if not (
            venue.lower() in event_venue.lower()
            or event_venue.lower() in venue.lower()
        ):
            continue

        event_end = date.fromisoformat(event["dates"]["end"])

        # Event must have ended within lookback_days before the blog post
        if event_end > pub_date:
            continue
        if (pub_date - event_end).days > lookback_days:
            continue

        # Prefer most recent event
        if best_end_date is None or event_end > best_end_date:
            best_match = event["id"]
            best_end_date = event_end

    return best_match, venue


def _load_blog_links() -> dict:
    """Load existing blog links."""
    if BLOG_LINKS_PATH.exists():
        with open(BLOG_LINKS_PATH) as f:
            return json.load(f)
    return {}


def _save_blog_links(blog_links: dict):
    """Save blog links, preserving key order and comment."""
    with open(BLOG_LINKS_PATH, "w") as f:
        json.dump(blog_links, f, indent=2, ensure_ascii=False)
        f.write("\n")


def discover_blog_links(events: list[dict]) -> dict:
    """Discover blog recap posts and match them to events.

    Fetches the RSS feed, matches posts to events by venue + date proximity,
    and merges results into blog_links.json (preserving manual entries).

    Returns the updated blog_links dict.
    """
    print("\nDiscovering blog recap links from RSS feed...")

    items = _fetch_rss_items()
    if not items:
        print("  No blog posts found in RSS feed")
        return _load_blog_links()

    print(f"  Found {len(items)} blog posts in RSS feed")

    slug_map = _build_venue_slug_map()
    blog_links = _load_blog_links()
    new_links = 0

    for item in items:
        event_id, venue = _match_blog_to_event(item, events, slug_map)
        if not event_id:
            continue

        # Build the link entry
        entry = {
            "date": item["pub_date"].isoformat() if item["pub_date"] else "",
            "title": item["title"],
            "url": item["link"],
        }

        # Ensure event has an entry in blog_links
        if event_id not in blog_links:
            blog_links[event_id] = []

        # Deduplicate by URL
        existing_urls = {e["url"] for e in blog_links[event_id]}
        if item["link"] in existing_urls:
            continue

        blog_links[event_id].append(entry)
        new_links += 1
        print(f"  + Matched: {item['title']!r} -> {event_id} ({venue})")

    if new_links:
        _save_blog_links(blog_links)
        print(f"  Added {new_links} new blog links")
    else:
        print("  No new blog links to add")

    return blog_links


if __name__ == "__main__":
    # Standalone: load database and run discovery
    from ingestion.config import RACE_DATABASE_PATH

    with open(RACE_DATABASE_PATH) as f:
        db = json.load(f)

    discover_blog_links(db["events"])
