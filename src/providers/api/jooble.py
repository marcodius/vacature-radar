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
        "land": "NL",
    }


def _locaties(config):
    """Lijst zoeklocaties: 'locations' (lijst) of 'locatie' (enkel), val terug op NL."""
    locs = config.get("locations")
    if locs is None:
        locs = [config.get("locatie", "Nederland")]
    if isinstance(locs, str):
        locs = [locs]
    schoon = [str(l).strip() for l in locs if str(l).strip()]
    return schoon or ["Nederland"]


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    locaties = _locaties(config)
    trefwoorden = config.get("trefwoorden", STANDAARD_TREFWOORDEN)
    if isinstance(trefwoorden, str):
        trefwoorden = [trefwoorden]

    api_key = os.environ.get("JOOBLE_API_KEY")
    if not api_key:
        print("[Jooble] Geen JOOBLE_API_KEY in environment. Bron wordt overgeslagen.")
        return []

    gezien, resultaat = set(), []
    for location in locaties:
        for keywords in trefwoorden:
            if len(resultaat) >= max_resultaten:
                break
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
                print(f"[Jooble] '{keywords}' @ '{location}' mislukt: {fout}. Overslaan.")
    print(f"[Jooble] {len(resultaat)} vacatures uit {len(locaties)} locatie(s) × "
          f"{len(trefwoorden)} zoekterm(en).")
    return resultaat[:max_resultaten]
