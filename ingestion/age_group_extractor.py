"""Extract age group tags from event names and categories."""

from ingestion.config import AGE_GROUP_PATTERN, AGE_GROUP_NORMALIZE


def extract_age_groups(event_name: str, categories: list) -> list:
    """Extract age groups (U10-U21) from event name and categories.

    Returns sorted list of normalized age group strings.
    """
    found = set()

    # Search event name
    for match in AGE_GROUP_PATTERN.finditer(event_name):
        raw = match.group(1).lower()
        found.add(AGE_GROUP_NORMALIZE.get(raw, raw.upper()))

    # Search categories (may contain "U10/U12/U14/U16" or similar)
    for cat in categories:
        for match in AGE_GROUP_PATTERN.finditer(cat):
            raw = match.group(1).lower()
            found.add(AGE_GROUP_NORMALIZE.get(raw, raw.upper()))

    # Sort by age number
    return sorted(found, key=lambda x: int(x[1:]))
