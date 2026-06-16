"""API-provider voor Vacatures Overheid (CSO Vacature API).

Vacatures van WerkenvoorNederland.nl / WerkenbijdeOverheid.nl. Open data (CC-0),
maar de API vereist een sleutel uit een account. Sleutel via environment
variable CSO_API_KEY, nooit uit code. Zonder sleutel: niets (geen mock).
Docs: https://docs.api.cso20.net/
"""

import os

import requests

NAAM = "Vacatures Overheid"
API_URL = "https://api.cso20.net/v1/JobAPI/getJobs.json"


def _normaliseer(item):
    return {
        "titel": item.get("titel") or item.get("title") or "Onbekende functie",
        "bedrijf": item.get("organisatie") or item.get("bedrijf") or item.get("company") or "Overheid",
        "locatie": item.get("locatie") or item.get("standplaats") or item.get("location") or "Onbekend",
        "url": item.get("url") or item.get("link") or "",
        "omschrijving": item.get("omschrijving") or item.get("description") or "",
        "datum": item.get("datum") or item.get("publicatiedatum") or item.get("date") or "",
        "bron": NAAM,
    }


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    api_key = os.environ.get("CSO_API_KEY")
    if not api_key:
        print("[Overheid] Geen CSO_API_KEY in environment. Bron wordt overgeslagen.")
        return []
    try:
        response = requests.post(
            API_URL,
            json={"apiKey": api_key, "limit": max_resultaten},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("vacatures") or data.get("jobs") or data.get("results") or []
        return [_normaliseer(i) for i in items][:max_resultaten]
    except Exception as fout:  # noqa: BLE001
        print(f"[Overheid] Ophalen mislukt: {fout}. Bron wordt overgeslagen.")
        return []
