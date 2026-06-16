"""Scraper voor publieke Indeed zoekresultaatpagina's.

Gebruikt de normale publieke zoekresultaat-HTML. Deze provider gebruikt geen
login, cookies, sessietokens of browser-automation; blokkades worden door
_polite netjes afgevangen.
"""

from urllib.parse import parse_qs, urlencode, urljoin, urlparse

from . import _polite

NAAM = "Indeed"
BASIS = "https://nl.indeed.com"
ZOEK_URL = "https://nl.indeed.com/jobs"


def _tekst(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _page_urls(config):
    urls = []
    queries = _polite.lijst_config(config, "query", "queries", "crm")
    locaties = _polite.lijst_config(config, "location", "locations", config.get("locatie", "Nederland"))
    for query in queries:
        for locatie in locaties or ["Nederland"]:
            for p in range(0, int(config.get("max_pages", 2))):
                params = {
                    "q": query,
                    "l": locatie,
                    "start": p * 10,
                }
                if config.get("radius") is not None:
                    params["radius"] = str(config["radius"])
                urls.append(config.get("base_url", ZOEK_URL) + "?" + urlencode(params))
    return urls


def _job_key(card, link):
    for el in (card, link):
        if not el:
            continue
        for attr in ("data-jk", "data-jobkey", "data-id"):
            waarde = el.get(attr)
            if waarde:
                return waarde
    href = link.get("href", "") if link else ""
    qs = parse_qs(urlparse(href).query)
    return (qs.get("jk") or [""])[0]


def _vacature_url(card, link):
    key = _job_key(card, link)
    if key:
        return f"{BASIS}/viewjob?jk={key}"
    return urljoin(BASIS, link.get("href", "")) if link else ""


def _parse(html):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[{NAAM}] beautifulsoup4 niet geinstalleerd. Bron wordt overgeslagen.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("div.job_seen_beacon, div[data-jk], td.resultContent")
    resultaat = []
    gezien = set()

    for card in cards:
        link = card.select_one('a[href*="/viewjob"], a[href*="/rc/clk"], a[data-jk]')
        titel_el = card.select_one("h2.jobTitle span[title], h2.jobTitle span, a span[title]")
        titel = (titel_el.get("title") if titel_el and titel_el.get("title") else _tekst(titel_el))
        if not titel and link:
            titel = _tekst(link)
        url = _vacature_url(card, link)
        if not titel or not url or url in gezien:
            continue

        bedrijf = _tekst(card.select_one('[data-testid="company-name"], .companyName, span.companyName'))
        locatie = _tekst(card.select_one('[data-testid="text-location"], .companyLocation, div.companyLocation'))
        samenvatting = _tekst(card.select_one('.job-snippet, [data-testid="jobsnippet"]'))
        datum = _tekst(card.select_one('[data-testid="myJobsStateDate"], .date'))

        gezien.add(url)
        resultaat.append({
            "titel": titel,
            "bedrijf": bedrijf or "Onbekend bedrijf",
            "locatie": locatie or "Nederland",
            "url": url,
            "omschrijving": samenvatting,
            "datum": datum,
            "bron": NAAM,
        })
    return resultaat


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    gezien, resultaat = set(), []
    for html in htmls:
        for vacature in _parse(html):
            if vacature["url"] in gezien:
                continue
            gezien.add(vacature["url"])
            resultaat.append(vacature)
    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[Indeed] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
