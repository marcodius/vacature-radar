"""Handmatige fallback-provider voor LinkedIn, Indeed en vergelijkbare bronnen.

Automatische scraping kan per platform via een eigen provider worden ingericht.
Deze provider blijft beschikbaar voor vacatures die handmatig zijn toegevoegd in
data/manual_links.json, bijvoorbeeld zolang een automatische scraper nog niet
bestaat of wanneer een losse vacature snel moet worden meegenomen.

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


def _verrijk_linkedin(vacature):
    """Vul de omschrijving van een gepinde LinkedIn-vacature aan via de guest-
    endpoint, zodat hij volwaardig scoort i.p.v. alleen op titel+locatie. Faalt
    stil (dan blijft de vacature gewoon zichtbaar via de score-vloer)."""
    url = vacature.get("url", "")
    if "linkedin.com/jobs/view/" not in url:
        return
    if len((vacature.get("omschrijving") or "").strip()) >= 200:
        return
    try:
        import requests
        from bs4 import BeautifulSoup

        from providers.scrape import linkedin as li
        jid = li._job_id(url)
        if not jid:
            return
        resp = requests.get(
            li.DETAIL_URL + jid,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                     "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                     "Accept-Language": "nl-NL,nl;q=0.9"},
            timeout=20,
        )
        if resp.status_code != 200:
            return
        body = BeautifulSoup(resp.text, "html.parser").select_one(
            ".show-more-less-html__markup, .description__text")
        tekst = " ".join((body.get_text(" ", strip=True) if body else "").split())
        if tekst:
            vacature["omschrijving"] = tekst[:12000]
    except Exception:  # noqa: BLE001
        pass

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
    resultaat = [_normaliseer(i, bron_key) for i in geselecteerd]
    if bron_key == "linkedin_manual":
        for v in resultaat:
            _verrijk_linkedin(v)
    print(f"[Manual] {len(resultaat)} handmatige link(s) voor {bron_key}.")
    return resultaat
