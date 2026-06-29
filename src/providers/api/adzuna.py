"""API-provider voor Adzuna Nederland.

Vereist ADZUNA_APP_ID en ADZUNA_APP_KEY uit environment variables, nooit uit
code. 'trefwoorden' mag een string of lijst zijn; per term wordt gezocht.
Docs: https://developer.adzuna.com/
"""

import os
import time

import requests

NAAM = "Adzuna"
API_URL = "https://api.adzuna.com/v1/api/jobs/nl/search/1"


def _get_met_retry(params, pogingen=3):
    """GET met backoff bij tijdelijke fouten (503/429/timeout). Geeft JSON of
    None. Adzuna gaf in de praktijk losse 503's waardoor zoektermen wegvielen."""
    for poging in range(pogingen):
        try:
            resp = requests.get(API_URL, params=params, timeout=30)
            if resp.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(f"HTTP {resp.status_code}")
            resp.raise_for_status()
            return resp.json()
        except (requests.HTTPError, requests.Timeout, requests.ConnectionError):
            if poging == pogingen - 1:
                raise
            time.sleep(2 ** poging)  # 1s, 2s, 4s
    return None

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
        "land": "NL",
    }


def _locaties(config):
    """Lijst zoeklocaties: 'locations' (lijst) of 'locatie' (enkel), anders [""]."""
    locs = config.get("locations")
    if locs is None:
        enkel = config.get("locatie", "")
        locs = [enkel] if enkel else [""]
    if isinstance(locs, str):
        locs = [locs]
    schoon = [str(l).strip() for l in locs if str(l).strip()]
    return schoon or [""]


def fetch(config):
    max_resultaten = config.get("max_resultaten", 50)
    per_page = int(config.get("results_per_page", 25))
    distance = config.get("distance_km")
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("[Adzuna] ADZUNA_APP_ID/ADZUNA_APP_KEY ontbreken. Bron wordt overgeslagen.")
        return []

    trefwoorden = config.get("trefwoorden", STANDAARD_TREFWOORDEN)
    if isinstance(trefwoorden, str):
        trefwoorden = [trefwoorden] if trefwoorden else [""]
    locaties = _locaties(config)

    gezien, resultaat = set(), []
    for locatie in locaties:
        for what in trefwoorden:
            if len(resultaat) >= max_resultaten:
                break
            params = {
                "app_id": app_id, "app_key": app_key,
                "results_per_page": per_page, "content-type": "application/json",
            }
            if what:
                params["what"] = what
            if locatie:
                params["where"] = locatie
                if distance:
                    params["distance"] = distance
            try:
                data = _get_met_retry(params)
                for item in ((data or {}).get("results") or []):
                    v = _normaliseer(item)
                    if v["url"] and v["url"] in gezien:
                        continue
                    gezien.add(v["url"])
                    resultaat.append(v)
            except Exception as fout:  # noqa: BLE001
                print(f"[Adzuna] '{what}' @ '{locatie or 'NL'}' mislukt: {fout}. Overslaan.")
    print(f"[Adzuna] {len(resultaat)} vacatures uit {len(locaties)} locatie(s) × "
          f"{len(trefwoorden)} zoekterm(en).")
    return resultaat[:max_resultaten]
