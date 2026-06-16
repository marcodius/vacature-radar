"""API-provider voor Jooble NL (gratis REST-API).

Sleutel via environment variable JOOBLE_API_KEY, nooit uit code.
POST https://jooble.org/api/{sleutel} met JSON {keywords, location}.
'trefwoorden' mag een string of lijst zijn; bij een lijst zoeken we per term.
Docs: https://help.jooble.org/en/support/solutions/articles/60001448238
"""

import os

import requests

NAAM = "Jooble"
API_BASIS = "https://jooble.org/api/"

# Standaard zoektermen (Kevin) als de config er geen meegeeft.
STANDAARD_TREFWOORDEN = [
    "CRM Specialist", "Salesforce beheerder", "Revenue Operations Specialist",
    "Operations Specialist", "Projectcoördinator",
]


def _normaliseer(item):
    return {
        "titel": item.get("title") or "Onbekende functie",
        "bedrijf": item.get("company") or "Onbekend bedrijf",
        "locatie": item.get("location") or "Onbekend",
        "url": item.get("link") or "",
        "omschrijving": item.get("snippet") or "",
        "datum": (item.get("updated") or "")[:10],
        "bron": NAAM,
    }


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    location = config.get("locatie", "Nederland")
    trefwoorden = config.get("trefwoorden", STANDAARD_TREFWOORDEN)
    if isinstance(trefwoorden, str):
        trefwoorden = [trefwoorden]

    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        print("[Jooble] Geen JOOBLE_API_KEY in environment. Bron wordt overgeslagen.")
        return []

    gezien, resultaat = set(), []
    for keywords in trefwoorden:
        try:
            response = requests.post(
                API_BASIS + api_key,
                json={"keywords": keywords, "location": location},
                timeout=30,
            )
            response.raise_for_status()
            for item in (response.json().get("jobs") or []):
                v = _normaliseer(item)
                if v["url"] and v["url"] in gezien:
                    continue
                gezien.add(v["url"])
                resultaat.append(v)
        except Exception as fout:  # noqa: BLE001
            print(f"[Jooble] Zoekterm '{keywords}' mislukt: {fout}. Overslaan.")
    return resultaat[:max_resultaten]
