"""Talent.com-specifieke scraper.

De generieke scraper faalt op Talent.com: de ankertekst van de detaillink is de
knop 'Laat meer zien' en de URL is /view?id=<cijfers> zonder slug, dus de titel
werd altijd 'Laat meer zien' en de relevantie-voorfilter matchte nooit (0 van
honderden). De echte velden staan in de job-cards: h2[class*=JobCard_title]
(titel), [class*=JobCard_company] (bedrijf), [class*=JobCard_location] (locatie),
met een a[href*=/view] als detaillink. Deze provider parseert die kaarten.
"""

from urllib.parse import urljoin

from . import _polite
from .. import relevance

NAAM = "Talent.com"
BASIS = "https://nl.talent.com"


def _page_urls(config):
    return _polite.bouw_zoek_urls(
        config["base_url"],
        config,
        config.get("query_param", "k"),
        location_param=config.get("location_param", "l"),
        page_param=config.get("page_param", "p"),
        page_start=int(config.get("page_start", 1)),
    )


def _tekst(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _parse(html, naam, land):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    soup = BeautifulSoup(html, "html.parser")
    resultaat, gezien = [], set()
    for titel_el in soup.select('h2[class*="JobCard_title"]'):
        titel = _tekst(titel_el)
        if not titel or len(titel) < 3:
            continue
        # Loop omhoog tot de kaart die ook de /view-detaillink bevat.
        card, href = titel_el, None
        for _ in range(6):
            card = card.parent
            if card is None:
                break
            anker = card.select_one('a[href*="/view"]')
            if anker and anker.get("href"):
                href = anker["href"]
                break
        if not href or card is None:
            continue
        url = urljoin(BASIS, href)
        if url in gezien:
            continue
        gezien.add(url)
        resultaat.append({
            "titel": titel,
            "bedrijf": _tekst(card.select_one('[class*="JobCard_company"]')) or "Onbekend bedrijf",
            "locatie": _tekst(card.select_one('[class*="JobCard_location"]')) or "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": "",
            "bron": naam,
            "land": land,
        })
    return resultaat


def fetch(config):
    naam = config.get("naam") or NAAM
    if not config.get("base_url"):
        print(f"[{naam}] Geen 'base_url' in config. Bron wordt overgeslagen.")
        return []
    land = config.get("country", "")
    htmls = _polite.haal_pagina_html(naam, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_parse(html, naam, land))
    resultaat = _polite.unieke_vacatures(resultaat)

    filter_aan, trefwoorden = relevance.filter_config(config)
    if filter_aan:
        totaal = len(resultaat)
        resultaat = [v for v in resultaat
                     if relevance.is_relevant(v["titel"], v["url"], trefwoorden=trefwoorden)]
        print(f"[{naam}] {len(resultaat)} van {totaal} vacatures relevant na voorfilter "
              f"(uit {len(htmls)} pagina's).")
    else:
        print(f"[{naam}] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 150)]
