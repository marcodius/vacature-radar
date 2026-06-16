"""Nette scraper voor Randstad — publieke vacaturezoekpagina's.

robots.txt staat `/vacatures/` toe. De zoekresultaten zijn server-rendered:
elke vacature is een `<article class="card item">` met een `<h2>`-titel, de
detaillink (`/vacatures/<id>/<slug>`) en een rij `<span class="simplelist__item--text">`
met (in volgorde) locatie, salaris, uren en opleidingsniveau. Bedrijf en datum
staan niet op de kaart.

Volgt de polite-regels uit docs/source_policy.md via _polite (robots, delay,
caching, user-agent, stop bij blokkade). Standaard aan.
"""

from urllib.parse import urlencode, urljoin

from . import _polite

NAAM = "Randstad"
BASIS = "https://www.randstad.nl"
ZOEK_URL = "https://www.randstad.nl/vacatures/"


def _page_urls(config):
    zoek = config.get("base_url", ZOEK_URL)
    queries = _polite.lijst_config(config, "query", "queries", "")
    urls = []
    for query in queries or [""]:
        for p in range(1, int(config.get("max_pages", 2)) + 1):
            params = {"page": p}
            if query:
                params["zoekterm"] = query
            urls.append(zoek + "?" + urlencode(params))
    return urls


def _is_salaris(tekst):
    t = tekst.lower()
    return "€" in tekst or "per maand" in t or "per jaar" in t or "per uur" in t


def _parse(html):
    """Parse vacaturekaarten uit een zoekresultaatpagina."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[{NAAM}] beautifulsoup4 niet geinstalleerd. Bron wordt overgeslagen.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    resultaat = []
    for card in soup.select("article.card.item"):
        link = card.select_one('a[href*="/vacatures/"]')
        kop = card.find(["h2", "h3"])
        if not link or not kop:
            continue
        titel = " ".join(kop.get_text(" ", strip=True).split())
        url = urljoin(BASIS, link.get("href", ""))

        items = [s.get_text(" ", strip=True) for s in card.select(".simplelist__item--text")]
        items = [i for i in items if i]
        # Locatie = eerste niet-salaris-item; salaris = item met euro/periode.
        locatie = next((i for i in items if not _is_salaris(i)), "Nederland")
        # Korte omschrijving = alle kenmerken samen (bevat ook salaris -> scoremodel
        # kan het minimumsalaris detecteren).
        omschrijving = " · ".join(items)

        resultaat.append({
            "titel": titel or "Onbekende functie",
            "bedrijf": "Onbekend bedrijf",
            "locatie": locatie,
            "url": url,
            "omschrijving": omschrijving,
            "datum": "",
            "bron": NAAM,
        })
    return resultaat


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)

    gezien, resultaat = set(), []
    for html in htmls:
        for v in _parse(html):
            if v["url"] in gezien:
                continue
            gezien.add(v["url"])
            resultaat.append(v)

    # Terugval: als de kaartstructuur wijzigt, haal in elk geval de links eruit.
    if not resultaat and htmls:
        for html in htmls:
            for v in _polite.extraheer_vacatures(
                html, "/vacatures/", BASIS, NAAM, detail_regex=r"/vacatures/\d"):
                if v["url"] not in gezien:
                    gezien.add(v["url"])
                    resultaat.append(v)

    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[Randstad] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
