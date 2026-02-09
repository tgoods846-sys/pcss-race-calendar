"""Test the SUMMARY parser against all live iCal SUMMARY strings.

Run: python3 -m pytest tests/test_summary_parser.py -v
"""
import pytest
from ingestion.summary_parser import parse_summary


TEST_CASES = [
    {
        "input": "U16 Trudi Bolinder Qualifier- 3 SG- Bogus Basin-Canceled",
        "name": "U16 Trudi Bolinder Qualifier",
        "disciplines": ["SG"],
        "discipline_counts": {"SG": 3},
        "venue": "Bogus Basin",
        "canceled": True,
    },
    {
        "input": "U14 Qualifier- 3 SG- Tamarack",
        "name": "U14 Qualifier",
        "disciplines": ["SG"],
        "discipline_counts": {"SG": 3},
        "venue": "Tamarack",
        "canceled": False,
    },
    {
        "input": "South Series- 2 GS- Snowbird",
        "name": "South Series",
        "disciplines": ["GS"],
        "discipline_counts": {"GS": 2},
        "venue": "Snowbird",
        "canceled": False,
    },
    {
        "input": "YSL Kombi- Utah Olympic Park",
        "name": "YSL Kombi",
        "disciplines": ["K"],
        "discipline_counts": {"K": 1},
        "venue": "Utah Olympic Park",
        "canceled": False,
    },
    {
        "input": "WR Elite- 2 SL/2 GS- Snowbird/Utah Olympic Park",
        "name": "WR Elite",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 2, "GS": 2},
        "venue": "Snowbird/Utah Olympic Park",
        "canceled": False,
    },
    {
        "input": "U16 Laura Flood Qualifier- 2 SL/2 GS/2 SG- Sun Valley",
        "name": "U16 Laura Flood Qualifier",
        "disciplines": ["SL", "GS", "SG"],
        "discipline_counts": {"SL": 2, "GS": 2, "SG": 2},
        "venue": "Sun Valley",
        "canceled": False,
    },
    {
        "input": "South Series- SL/GS- Sundance",
        "name": "South Series",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 1},
        "venue": "Sundance",
        "canceled": False,
    },
    {
        "input": "U14 David Wright Qualifier- 1 SL/ 2 GS- Park City",
        "name": "U14 David Wright Qualifier",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 2},
        "venue": "Park City",
        "canceled": False,
    },
    {
        "input": "North Series Cranston Cup- SL/GS- Bogus Basin",
        "name": "North Series Cranston Cup",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 1},
        "venue": "Bogus Basin",
        "canceled": False,
    },
    {
        "input": "Western Region Junior Champs- SL/GS/SG- Grand Targhee",
        "name": "Western Region Junior Champs",
        "disciplines": ["SL", "GS", "SG"],
        "discipline_counts": {"SL": 1, "GS": 1, "SG": 1},
        "venue": "Grand Targhee",
        "canceled": False,
    },
    {
        "input": "YSL Finals- SL/GS- Snowbasin",
        "name": "YSL Finals",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 1},
        "venue": "Snowbasin",
        "canceled": False,
    },
    {
        "input": "WR U16 Regionals- SL/GS/SG- Palisades",
        "name": "WR U16 Regionals",
        "disciplines": ["SL", "GS", "SG"],
        "discipline_counts": {"SL": 1, "GS": 1, "SG": 1},
        "venue": "Palisades",
        "canceled": False,
    },
    {
        "input": "IMD Finals- SL/GS- Park City",
        "name": "IMD Finals",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 1, "GS": 1},
        "venue": "Park City",
        "canceled": False,
    },
    {
        "input": "WR Devo- 2 SL/2 GS- Mission Ridge",
        "name": "WR Devo",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 2, "GS": 2},
        "venue": "Mission Ridge",
        "canceled": False,
    },
    {
        "input": "WR U14 Regional Championships- SL/GS/SG- Mt. Bachelor",
        "name": "WR U14 Regional Championships",
        "disciplines": ["SL", "GS", "SG"],
        "discipline_counts": {"SL": 1, "GS": 1, "SG": 1},
        "venue": "Mt. Bachelor",
        "canceled": False,
    },
    {
        "input": "IMD Champs- SL/GS/PS- Jackson Hole",
        "name": "IMD Champs",
        "disciplines": ["SL", "GS", "PS"],
        "discipline_counts": {"SL": 1, "GS": 1, "PS": 1},
        "venue": "Jackson Hole",
        "canceled": False,
    },
    {
        "input": "Tri Divisionals- SL/GS/SG- Snowbasin",
        "name": "Tri Divisionals",
        "disciplines": ["SL", "GS", "SG"],
        "discipline_counts": {"SL": 1, "GS": 1, "SG": 1},
        "venue": "Snowbasin",
        "canceled": False,
    },
    {
        "input": "WR Devo FIS-Sun Valley",
        "name": "WR Devo FIS",
        "disciplines": [],
        "discipline_counts": {},
        "venue": "Sun Valley",
        "canceled": False,
    },
    {
        "input": "USSS U16 Nationals-Snowking",
        "name": "USSS U16 Nationals",
        "disciplines": [],
        "discipline_counts": {},
        "venue": "Snow King",
        "canceled": False,
    },
    {
        "input": "U12/U14 Spring Fling- SL/GS/K- Grand Targhee",
        "name": "U12/U14 Spring Fling",
        "disciplines": ["SL", "GS", "K"],
        "discipline_counts": {"SL": 1, "GS": 1, "K": 1},
        "venue": "Grand Targhee",
        "canceled": False,
    },
    {
        "input": "IMC SnowCup- 2 SL/2 GS- Snowbird",
        "name": "IMC SnowCup",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 2, "GS": 2},
        "venue": "Snowbird",
        "canceled": False,
    },
    {
        "input": "Elite Spring Series- 2 SL/2 GS- Palisades",
        "name": "Elite Spring Series",
        "disciplines": ["SL", "GS"],
        "discipline_counts": {"SL": 2, "GS": 2},
        "venue": "Palisades",
        "canceled": False,
    },
    {
        "input": "WR Spring Speed- 2 DH/2 SG- Mt. Bachelor",
        "name": "WR Spring Speed",
        "disciplines": ["DH", "SG"],
        "discipline_counts": {"DH": 2, "SG": 2},
        "venue": "Mt. Bachelor",
        "canceled": False,
    },
    {
        "input": "WR U14 Flight School- Palisaides",
        "name": "WR U14 Flight School",
        "disciplines": [],
        "discipline_counts": {},
        "venue": "Palisades",
        "canceled": False,
    },
]


@pytest.mark.parametrize(
    "case", TEST_CASES, ids=[c["input"][:50] for c in TEST_CASES]
)
def test_summary_parser(case):
    result = parse_summary(case["input"])
    assert result["event_name"] == case["name"], (
        f"Name: expected '{case['name']}', got '{result['event_name']}'"
    )
    assert result["disciplines"] == case["disciplines"], (
        f"Disciplines: expected {case['disciplines']}, got {result['disciplines']}"
    )
    assert result["discipline_counts"] == case["discipline_counts"], (
        f"Counts: expected {case['discipline_counts']}, got {result['discipline_counts']}"
    )
    assert result["venue"] == case["venue"], (
        f"Venue: expected '{case['venue']}', got '{result['venue']}'"
    )
    assert result["canceled"] == case["canceled"], (
        f"Canceled: expected {case['canceled']}, got {result['canceled']}"
    )
