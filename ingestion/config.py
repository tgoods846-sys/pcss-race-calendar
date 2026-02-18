"""Central configuration for the PCSS race calendar ingestion pipeline."""

import os
import re
from pathlib import Path

# --- Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RACE_DATABASE_PATH = DATA_DIR / "race_database.json"
USSA_SEEDS_PATH = DATA_DIR / "ussa_manual_events.json"
BLOG_LINKS_PATH = DATA_DIR / "blog_links.json"
PCSS_RESULTS_CACHE_PATH = DATA_DIR / "pcss_results_cache.json"

# --- IMD iCal Feed ---
IMD_ICAL_URL = "https://imdalpine.org/?post_type=tribe_events&ical=1&eventDisplay=list"
IMD_ICAL_PAST_URL = "https://imdalpine.org/?post_type=tribe_events&ical=1&eventDisplay=past"
IMD_EVENTS_URL = "https://imdalpine.org/events/"
IMD_RESULTS_URL = "https://imdalpine.org/race-results/"

# --- Blog RSS Feed ---
BLOG_RSS_URL = "https://www.simsportsarena.com/blog-feed.xml"

# Slug abbreviations that don't match any KNOWN_VENUES slugification
VENUE_SLUG_ALIASES = {
    "uop": "Utah Olympic Park",
    "jhmr": "Jackson Hole",
    "mt-bachelor": "Mt. Bachelor",
}

# --- PCSS Detection Patterns (word-boundary regex from existing monitor) ---
PCSS_PATTERNS = [
    re.compile(r"\bPCSS\b", re.IGNORECASE),
    re.compile(r"\bPark City\b", re.IGNORECASE),
    re.compile(r"\bPark City SS\b", re.IGNORECASE),
    re.compile(r"\bPark City Ski\b", re.IGNORECASE),
]

# --- Discipline Parsing ---
# Matches patterns like "2 SL", "2SL", "SL", "3 SG" — with optional run count
# Uses \s* (not \s+) to handle "2SL" without space
DISCIPLINE_PATTERN = re.compile(r"\b(\d+\s*)?(SL|GS|SG|DH|PS|AC|K|Kombi)\b", re.IGNORECASE)

DISCIPLINE_NORMALIZE = {
    "sl": "SL",
    "gs": "GS",
    "sg": "SG",
    "dh": "DH",
    "ps": "PS",
    "ac": "AC",
    "k": "K",
    "kombi": "K",
}

# --- Age Group Extraction ---
AGE_GROUP_PATTERN = re.compile(r"\b(U10|U12|U14|U16|U18|U19|U21)\b", re.IGNORECASE)

AGE_GROUP_NORMALIZE = {
    "u10": "U10",
    "u12": "U12",
    "u14": "U14",
    "u16": "U16",
    "u18": "U18",
    "u19": "U19",
    "u21": "U21",
}

# Keyword → implied age groups (fallback when no explicit U-codes found)
AGE_GROUP_KEYWORDS = {
    r"\bYSL\b": ["U10", "U12"],
    r"\bIMC\b": ["U14", "U16"],
    r"\bDevo\b": ["U16", "U18", "U21"],
    r"\bNJR\b": ["U16", "U18", "U21"],
    r"\bFIS\b": ["U16", "U18", "U21"],
    r"\bNationals\b": ["U16"],
}

# --- Known Venues (for disambiguation in SUMMARY parsing) ---
KNOWN_VENUES = [
    "Utah Olympic Park",
    "Bogus Basin",
    "Tamarack",
    "Snowbird",
    "Sun Valley",
    "Sundance",
    "Park City",
    "Grand Targhee",
    "Snowbasin",
    "Palisades Tahoe",
    "Palisades",
    "Jackson Hole",
    "Mission Ridge",
    "Mt. Bachelor",
    "Snow King",
    "Beaver Mountain",
    "Brighton",
    "Soldier Mountain",
    "Brundage",
    "Schweitzer",
    "Red Lodge",
    "Big Sky",
    "Whitefish",
    "Lookout Pass",
    "Silver Mountain",
]

# --- Venue Typo Normalization ---
VENUE_NORMALIZE = {
    "Palisaides": "Palisades",
    "Snowking": "Snow King",
    "SnowKing": "Snow King",
    "snowking": "Snow King",
}

# --- Venue to State Mapping ---
VENUE_STATE_MAP = {
    "Utah Olympic Park": "UT",
    "Snowbird": "UT",
    "Park City": "UT",
    "Sundance": "UT",
    "Snowbasin": "UT",
    "Brighton": "UT",
    "Beaver Mountain": "UT",
    "Soldier Mountain": "ID",
    "Bogus Basin": "ID",
    "Tamarack": "ID",
    "Brundage": "ID",
    "Sun Valley": "ID",
    "Grand Targhee": "WY",
    "Jackson Hole": "WY",
    "Snow King": "WY",
    "Palisades Tahoe": "CA",
    "Palisades": "CA",
    "Mission Ridge": "WA",
    "Mt. Bachelor": "OR",
    "Schweitzer": "ID",
    "Red Lodge": "MT",
    "Big Sky": "MT",
    "Whitefish": "MT",
    "Lookout Pass": "ID",
    "Silver Mountain": "ID",
}

# --- Category → Circuit Mapping ---
CATEGORY_CIRCUIT_MAP = {
    "south series": "IMD",
    "north series": "IMD",
    "imd u14": "IMD",
    "imd u16": "IMD",
    "imc u16 qualifier": "IMD",
    "imc u14 qualifier": "IMD",
    "imd champs": "IMD",
    "imd finals": "IMD",
    "ysl": "IMD",
    "western region": "Western Region",
    "wr": "Western Region",
    "tri divisional": "IMD",
    "tri divisionals": "IMD",
    "fis": "FIS",
    "ussa": "USSA",
    "usss": "USSA",
    "us ski": "USSA",
}

# --- Canceled Detection ---
CANCELED_SUFFIX_PATTERN = re.compile(
    r"[-\s]*(Canceled|Cancelled|Postponed|Rescheduled)\s*$", re.IGNORECASE
)
