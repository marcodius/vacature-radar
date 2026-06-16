"""Provider voor Jooble (extra bron).

Jooble heeft een gratis REST-API. Je vraagt eenmalig een sleutel aan; die komt
uit de environment variable JOOBLE_API_KEY, nooit uit code.
Documentatie: https://help.jooble.org/en/support/solutions/articles/60001448238

Aanroep: POST https://jooble.org/api/{sleutel} met JSON {keywords, location}.
Respons: {"jobs": [{titel, locatie, snippet, link, company, updated, ...}]}.
"""

import os

import requests

NAAM = "Jooble"

API_BASIS = "https://jooble.org/api/"


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
    """Haal vacatures op. config is het 'jooble'-blok uit sources.json.

    'trefwoorden' mag een string zijn of een lijst zoektermen; bij een lijst
    voeren we per term een zoekopdracht uit en voegen we de resultaten samen
    (ontdubbeld op url).
    """
    max_resultaten = config.get("max_resultaten", 50)
    location = config.get("locatie", "Nederland")
    trefwoorden = config.get("trefwoorden", "")
    if isinstance(trefwoorden, str):
        trefwoorden = [trefwoorden]

    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        print(
            "[Jooble] JOOBLE_API_KEY ontbreekt in environment. Bron wordt overgeslagen."
        )
        return []

    gezien = set()
    resultaat = []
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
