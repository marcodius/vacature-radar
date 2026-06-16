"""Provider voor Jobicy (gratis remote-jobs API, geen sleutel).

Endpoint: https://jobicy.com/api/v2/remote-jobs  (JSON, GET, geen auth).
Jobicy vraagt om duidelijke bronvermelding en doorverwijzing naar hun site;
dat regelen we via 'bron' = "Jobicy" en de originele url.

Omdat Jobicy internationale remote-jobs levert, filteren we lokaal op
trefwoorden (config 'post_filter_keywords') zodat alleen CRM/operations/
SaaS-achtige functies overblijven.
Docs: https://jobi.cy/apidocs
"""

import re

import requests

NAAM = "Jobicy"

API_URL = "https://jobicy.com/api/v2/remote-jobs"


def _strip_html(tekst):
    return re.sub(r"<[^>]+>", " ", tekst or "").replace("&nbsp;", " ").strip()


def _normaliseer(item):
    return {
        "titel": item.get("jobTitle") or "Onbekende functie",
        "bedrijf": item.get("companyName") or "Onbekend bedrijf",
        "locatie": item.get("jobGeo") or "Remote",
        "url": item.get("url") or "",
        "omschrijving": _strip_html(item.get("jobExcerpt") or item.get("jobDescription") or ""),
        "datum": (item.get("pubDate") or "")[:10],
        "bron": NAAM,
    }


def _past_filter(vacature, trefwoorden):
    if not trefwoorden:
        return True
    tekst = (vacature["titel"] + " " + vacature["omschrijving"] + " " + vacature["locatie"]).lower()
    return any(t.lower() in tekst for t in trefwoorden)


def fetch(config):
    """Haal remote-jobs op. config is het 'jobicy'-blok uit sources.json."""
    max_resultaten = config.get("max_resultaten", 50)
    trefwoorden = config.get("post_filter_keywords", [])

    params = {"count": min(max_resultaten if max_resultaten else 50, 50)}
    # Optionele Jobicy-filters (bijv. tag / industry) uit config.
    if config.get("tag"):
        params["tag"] = config["tag"]
    if config.get("geo"):
        params["geo"] = config["geo"]

    try:
        response = requests.get(API_URL, params=params, timeout=30)
        response.raise_for_status()
        items = response.json().get("jobs") or []
    except Exception as fout:  # noqa: BLE001
        print(f"[Jobicy] Ophalen mislukt: {fout}. Bron wordt overgeslagen.")
        return []

    resultaat = []
    for item in items:
        v = _normaliseer(item)
        if _past_filter(v, trefwoorden):
            resultaat.append(v)
    print(f"[Jobicy] {len(resultaat)} van {len(items)} remote-jobs na filter.")
    return resultaat[:max_resultaten]
