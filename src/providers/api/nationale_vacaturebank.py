"""API-provider voor de Nationale Vacaturebank.

De Nationale Vacaturebank heeft geen gratis openbare API; officiele toegang
loopt via een API-sleutel uit een account. De sleutel komt uit de environment
variable NVB_API_KEY, nooit uit code. Zonder sleutel levert de provider niets op
(geen mock-data meer).
"""

import os

import requests

NAAM = "Nationale Vacaturebank"
API_URL = "https://api.nationalevacaturebank.nl/v1/vacatures"


def _normaliseer(item):
    return {
        "titel": item.get("titel") or item.get("title") or "Onbekende functie",
        "bedrijf": item.get("bedrijf") or item.get("company") or "Onbekend bedrijf",
        "locatie": item.get("locatie") or item.get("location") or "Onbekend",
        "url": item.get("url") or item.get("link") or "",
        "omschrijving": item.get("omschrijving") or item.get("description") or "",
        "datum": item.get("datum") or item.get("date") or "",
        "bron": NAAM,
    }


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    api_key = os.environ.get("NVB_API_KEY")
    if not api_key:
        print("[NVB] Geen NVB_API_KEY in environment. Bron wordt overgeslagen.")
        return []
    try:
        response = requests.get(
            API_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            params={"limit": max_resultaten},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("vacatures") or data.get("results") or []
        return [_normaliseer(i) for i in items][:max_resultaten]
    except Exception as fout:  # noqa: BLE001
        print(f"[NVB] Ophalen mislukt: {fout}. Bron wordt overgeslagen.")
        return []
