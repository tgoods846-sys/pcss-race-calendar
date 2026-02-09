"""Load manually-seeded USSA national/regional events."""

import json
from ingestion.config import USSA_SEEDS_PATH


def load_ussa_seeds() -> list:
    """Load USSA manual events from JSON file.

    Returns list of event dicts matching the race database schema.
    """
    if not USSA_SEEDS_PATH.exists():
        return []

    with open(USSA_SEEDS_PATH) as f:
        return json.load(f)
