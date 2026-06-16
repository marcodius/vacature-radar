"""Provider voor Arbeitnow (extra bron, standaard uit in versie 1).

Arbeitnow heeft een gratis, open API zonder sleutel.
Documentatie: https://www.arbeitnow.com/api/job-board-api
We filteren grof op Nederlandse locaties.
"""

import requests

NAAM = "Arbeitnow"

API_URL = "https://www.arbeitnow.com/api/job-board-api"

# Eenvoudige filter op Nederlandse locaties.
NL_TREFWOORDEN = [
    "netherlands", "nederland", "amsterdam", "rotterdam", "utrecht",
    "den haag", "the hague", "eindhoven", "groningen", "remote",
]


def _is_nederlands(item):
    locatie = (item.get("location") or "").lower()
    return any(t in locatie for t in NL_TREFWOORDEN)


def _normaliseer(item):
    return {
        "titel": item.get("title") or "Onbekende functie",
        "bedrijf": item.get("company_name") or "Onbekend bedrijf",
        "locatie": item.get("location") or ("Remote" if item.get("remote") else "Onbekend"),
        "url": item.get("url") or "",
        "omschrijving": item.get("description") or "",
        "datum": "",
        "bron": NAAM,
    }


def fetch(config):
    """Haal vacatures op. config is het 'arbeitnow'-blok uit sources.json."""
    max_resultaten = config.get("max_resultaten", 50)

    try:
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        items = data.get("data") or []
        nederlands = [i for i in items if _is_nederlands(i)]
        return [_normaliseer(i) for i in nederlands][:max_resultaten]
    except Exception as fout:  # noqa: BLE001
        print(f"[Arbeitnow] Ophalen mislukt: {fout}. Bron wordt overgeslagen.")
        return []
