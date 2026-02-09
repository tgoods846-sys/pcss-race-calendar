"""Extract age group tags from event names and categories."""

import re

from ingestion.config import AGE_GROUP_PATTERN, AGE_GROUP_NORMALIZE, AGE_GROUP_KEYWORDS


def extract_age_groups(event_name: str, categories: list) -> list:
    """Extract age groups (U10-U21) from event name and categories.

    First looks for explicit U-codes (U10, U14, etc.). If none found,
    falls back to keyword inference (e.g., "Devo" → U16/U18/U21).

    Returns sorted list of normalized age group strings.
    """
    found = set()

    # Search event name for explicit U-codes
    for match in AGE_GROUP_PATTERN.finditer(event_name):
        raw = match.group(1).lower()
        found.add(AGE_GROUP_NORMALIZE.get(raw, raw.upper()))

    # Search categories (may contain "U10/U12/U14/U16" or similar)
    for cat in categories:
        for match in AGE_GROUP_PATTERN.finditer(cat):
            raw = match.group(1).lower()
            found.add(AGE_GROUP_NORMALIZE.get(raw, raw.upper()))

    # Fallback: infer from keywords if no explicit U-codes found
    if not found:
        searchable = " ".join([event_name] + categories)
        for pattern, age_groups in AGE_GROUP_KEYWORDS.items():
            if re.search(pattern, searchable, re.IGNORECASE):
                found.update(age_groups)

    # Sort by age number
    return sorted(found, key=lambda x: int(x[1:]))
