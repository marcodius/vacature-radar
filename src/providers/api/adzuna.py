"""API-provider voor Adzuna Nederland.

Vereist ADZUNA_APP_ID en ADZUNA_APP_KEY uit environment variables, nooit uit
code. 'trefwoorden' mag een string of lijst zijn; per term wordt gezocht.
Docs: https://developer.adzuna.com/
"""

import os

import requests

NAAM = "Adzuna"
API_URL = "https://api.adzuna.com/v1/api/jobs/nl/search/1"

STANDAARD_TREFWOORDEN = [
    "Salesforce CRM HubSpot",
    "Revenue Operations RevOps Sales Operations",
    "Customer Success Operations Business Operations",
    "Projectcoördinator Implementatie Specialist",
]


def _normaliseer(item):
    company = item.get("company") or {}
    location = item.get("location") or {}
    return {
        "titel": item.get("title") or "Onbekende functie",
        "bedrijf": company.get("display_name") or "Onbekend bedrijf",
        "locatie": location.get("display_name") or "Onbekend",
        "url": item.get("redirect_url") or "",
        "omschrijving": item.get("description") or "",
        "datum": (item.get("created") or "")[:10],
        "bron": NAAM,
    }


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("[Adzuna] ADZUNA_APP_ID/ADZUNA_APP_KEY ontbreken. Bron wordt overgeslagen.")
        return []

    trefwoorden = config.get("trefwoorden", STANDAARD_TREFWOORDEN)
    if isinstance(trefwoorden, str):
        trefwoorden = [trefwoorden] if trefwoorden else [""]
    locatie = config.get("locatie", "")

    gezien, resultaat = set(), []
    for what in trefwoorden:
        params = {
            "app_id": app_id, "app_key": app_key,
            "results_per_page": max_resultaten, "content-type": "application/json",
        }
        if what:
            params["what"] = what
        if locatie:
            params["where"] = locatie
        try:
            response = requests.get(API_URL, params=params, timeout=30)
            response.raise_for_status()
            for item in (response.json().get("results") or []):
                v = _normaliseer(item)
                if v["url"] and v["url"] in gezien:
                    continue
                gezien.add(v["url"])
                resultaat.append(v)
        except Exception as fout:  # noqa: BLE001
            print(f"[Adzuna] Zoekterm '{what}' mislukt: {fout}. Overslaan.")
    return resultaat[:max_resultaten]
