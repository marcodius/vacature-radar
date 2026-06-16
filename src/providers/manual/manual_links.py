"""Manual-only provider voor LinkedIn en Indeed.

LinkedIn en Indeed worden NOOIT automatisch opgehaald of gescrapet. Er gaan geen
requests naar linkedin.com of indeed.com. Vacatures van deze platforms komen
uitsluitend binnen via handmatig toegevoegde links in data/manual_links.json.

Elke regel in dat bestand heeft een 'source' ("linkedin_manual" of
"indeed_manual"). Deze provider leest het bestand, filtert op de gevraagde
bron en normaliseert naar hetzelfde vacaturemodel als de andere bronnen.
Zowel Nederlandse (titel/bedrijf/locatie) als Engelse (title/company/location)
sleutels worden ondersteund.
"""

import json
import os

PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
DATA_PAD = os.path.join(PROJECT_DIR, "data", "manual_links.json")

BRON_LABEL = {
    "linkedin_manual": "LinkedIn (handmatig)",
    "indeed_manual": "Indeed (handmatig)",
}


def _normaliseer(item, bron_key):
    return {
        "titel": item.get("titel") or item.get("title") or "Onbekende functie",
        "bedrijf": item.get("bedrijf") or item.get("company") or "Onbekend bedrijf",
        "locatie": item.get("locatie") or item.get("location") or "Onbekend",
        "url": item.get("url") or item.get("link") or "",
        "omschrijving": item.get("omschrijving") or item.get("description")
        or item.get("notes") or "",
        "datum": item.get("datum") or item.get("date") or "",
        "bron": BRON_LABEL.get(bron_key, "Handmatig"),
    }


def fetch(config):
    """Lees handmatige links voor de gevraagde bron (config['_key'])."""
    bron_key = config.get("_key", "linkedin_manual")

    if not os.path.exists(DATA_PAD):
        print(f"[Manual] {DATA_PAD} bestaat niet. Geen handmatige links voor {bron_key}.")
        return []

    try:
        with open(DATA_PAD, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception as fout:  # noqa: BLE001
        print(f"[Manual] Lezen mislukt: {fout}. Overslaan.")
        return []

    if not isinstance(items, list):
        print("[Manual] manual_links.json moet een lijst zijn. Overslaan.")
        return []

    # Filter op de gevraagde bron. Regels zonder 'source' tellen mee bij LinkedIn
    # (terugvalgedrag voor oudere bestanden).
    geselecteerd = [
        i for i in items
        if i.get("source", "linkedin_manual") == bron_key
    ]
    return [_normaliseer(i, bron_key) for i in geselecteerd]
