"""Brand constants, paths, and format dimensions for social image generation."""

from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RACE_DB_PATH = DATA_DIR / "race_database.json"
FONTS_DIR = PROJECT_ROOT / "fonts"
LOGO_PATH = PROJECT_ROOT / "site" / "assets" / "sim_sports_logo_horizontal_dark.jpg"
OUTPUT_DIR = PROJECT_ROOT / "output" / "social"
VENUES_DIR = PROJECT_ROOT / "assets" / "venues"

# Brand colors
COLOR_BG = "#141414"
COLOR_PRIMARY = "#1190CB"
COLOR_WHITE = "#FFFFFF"
COLOR_MUTED = "#94A3B8"

# Discipline colors (from variables.css)
DISCIPLINE_COLORS = {
    "SL": "#2563EB",
    "GS": "#DC2626",
    "SG": "#EA580C",
    "DH": "#7C3AED",
    "PS": "#059669",
    "K": "#D97706",
    "AC": "#6366F1",
}

# Circuit colors
CIRCUIT_COLORS = {
    "IMD": "#475569",
    "Western Region": "#7C3AED",
    "USSA": "#DC2626",
    "FIS": "#2563EB",
}

# Image format dimensions
FORMATS = {
    "story": (1080, 1920),
    "post": (1080, 1080),
    "facebook": (1200, 630),
    "reel": (1080, 1920),
}

# Template types
TEMPLATE_TYPES = ["pre_race", "race_day", "weekly_preview"]

# Venue name → filename mapping (tries .jpg then .png)
VENUE_FILENAME_MAP = {
    "Snowbird": "snowbird",
    "Snowbasin": "snowbasin",
    "Park City": "park-city",
    "Sun Valley": "sun-valley",
    "Jackson Hole": "jackson-hole",
    "Palisades": "palisades-tahoe",
    "Palisades Tahoe": "palisades-tahoe",
    "Grand Targhee": "grand-targhee",
    "Sundance": "sundance",
    "Deer Valley": "deer-valley",
    "Bogus Basin": "bogus-basin",
    "Mammoth Mtn.": "mammoth",
    "Mission Ridge": "mission-ridge",
    "Mt. Bachelor": "mt-bachelor",
    "Utah Olympic Park": "utah-olympic-park",
    "Tamarack": "tamarack",
    "Schweitzer": "schweitzer",
    "Brighton": "brighton",
    "Snow King": "snow-king",
    "Big Sky": "big-sky",
    "JHMR": "jackson-hole",
    "Sugarbowl": "sugarbowl",
    "Rotarun": "rotarun",
}

# Per-venue horizontal crop alignment (0.0=left, 0.5=center, 1.0=right)
# Only needed for venues where center-crop misses important content
VENUE_CROP_ALIGN = {
    "palisades-tahoe": 0.75,
}
