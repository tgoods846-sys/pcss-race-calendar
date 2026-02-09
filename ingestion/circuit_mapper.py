"""Map iCal CATEGORIES to circuit types."""

from ingestion.config import CATEGORY_CIRCUIT_MAP


def map_circuit(categories: list, event_name: str) -> tuple:
    """Determine circuit and series from categories and event name.

    Returns (circuit: str, series: str).
    """
    circuit = "IMD"  # Default for IMD feed events
    series = ""

    # Check categories first (most reliable)
    for cat in categories:
        cat_lower = cat.lower().strip()

        # Direct match in map
        if cat_lower in CATEGORY_CIRCUIT_MAP:
            circuit = CATEGORY_CIRCUIT_MAP[cat_lower]
            series = cat.strip()
            break

        # Partial match
        for key, mapped_circuit in CATEGORY_CIRCUIT_MAP.items():
            if key in cat_lower:
                circuit = mapped_circuit
                series = cat.strip()
                break

    # If no series found from categories, try event name patterns
    if not series:
        name_lower = event_name.lower()
        if "south series" in name_lower:
            series = "South Series"
        elif "north series" in name_lower:
            series = "North Series"
        elif "ysl" in name_lower:
            series = "YSL"
            circuit = "IMD"
        elif "imd" in name_lower:
            series = "IMD"
        elif "wr " in name_lower or "western region" in name_lower:
            circuit = "Western Region"
            series = "Western Region"
        elif "usss" in name_lower or "ussa" in name_lower or "us ski" in name_lower:
            circuit = "USSA"
            series = "USSA"
        elif "fis" in name_lower:
            circuit = "FIS"
        elif "imc" in name_lower:
            series = "IMC"
            circuit = "IMD"
        elif "tri divisional" in name_lower:
            series = "Tri Divisionals"
            circuit = "IMD"
        elif "elite" in name_lower:
            series = "Elite"

    return circuit, series
