"""Tag events for PCSS relevance using word-boundary regex patterns."""

from ingestion.config import PCSS_PATTERNS


def is_pcss_relevant(event: dict) -> bool:
    """Check if an event is PCSS-relevant.

    Searches event name, venue, and description for PCSS-related terms.
    Uses the same word-boundary regex patterns from the existing monitor.
    """
    searchable_text = " ".join([
        event.get("event_name", ""),
        event.get("venue", ""),
        event.get("description", ""),
    ])

    for pattern in PCSS_PATTERNS:
        if pattern.search(searchable_text):
            return True

    return False
