"""Provider voor handmatig toegevoegde links (bijv. LinkedIn).

LinkedIn wordt NIET gescrapet. Je voegt zelf links toe in data/manual_links.json
(zie data/manual_links.example.json voor het formaat).
"""

import json
import os

NAAM = "Handmatig"

DATA_PAD = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "manual_links.json",
)


def _normaliseer(item):
    return {
        "titel": item.get("titel") or "Onbekende functie",
        "bedrijf": item.get("bedrijf") or "Onbekend bedrijf",
        "locatie": item.get("locatie") or "Onbekend",
        "url": item.get("url") or "",
        "omschrijving": item.get("omschrijving") or "",
        "datum": item.get("datum") or "",
        "bron": item.get("bron") or NAAM,
    }


def fetch(config):
    """Lees handmatige links uit data/manual_links.json."""
    if not os.path.exists(DATA_PAD):
        print(
            f"[Handmatig] {DATA_PAD} bestaat niet. "
            "Kopieer data/manual_links.example.json om links toe te voegen."
        )
        return []

    try:
        with open(DATA_PAD, "r", encoding="utf-8") as f:
            items = json.load(f)
        if not isinstance(items, list):
            print("[Handmatig] manual_links.json moet een lijst zijn. Overslaan.")
            return []
        return [_normaliseer(i) for i in items]
    except Exception as fout:  # noqa: BLE001
        print(f"[Handmatig] Lezen mislukt: {fout}. Bron wordt overgeslagen.")
        return []
