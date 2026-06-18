"""Scraper voor publieke LinkedIn vacaturezoekresultaten.

Gebruikt de publieke guest jobs endpoint. Deze provider gebruikt geen login,
cookies, sessietokens of browser-automation; blokkades worden door _polite
netjes afgevangen.
"""

import re
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from . import _polite

NAAM = "LinkedIn"
BASIS = "https://www.linkedin.com"
ZOEK_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
# Guest-endpoint met de volledige vacaturetekst (geen login nodig).
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"


def _schone_url(url):
    parsed = urlparse(url)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))


def _tekst(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _page_urls(config):
    afstand = str(config.get("distance", 25))
    urls = []
    queries = _polite.lijst_config(config, "query", "queries", "crm")
    locaties = _polite.lijst_config(config, "location", "locations", config.get("locatie", "Nederland"))
    geo_ids = config.get("geo_ids") or []
    for query in queries:
        for locatie in locaties or ["Nederland"]:
            for p in range(0, int(config.get("max_pages", 2))):
                params = {
                    "keywords": query,
                    "location": locatie,
                    "distance": afstand,
                    "start": p * 25,
                }
                if config.get("geo_id"):
                    params["geoId"] = str(config["geo_id"])
                urls.append(ZOEK_URL + "?" + urlencode(params))
        for geo_id in geo_ids:
            for p in range(0, int(config.get("max_pages", 2))):
                params = {
                    "keywords": query,
                    "geoId": str(geo_id),
                    "distance": afstand,
                    "start": p * 25,
                }
                urls.append(ZOEK_URL + "?" + urlencode(params))
    return urls


def _parse(html):
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[{NAAM}] beautifulsoup4 niet geinstalleerd. Bron wordt overgeslagen.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    cards = soup.select("li, div.base-card, div.job-search-card")
    resultaat = []
    gezien = set()

    for card in cards:
        link = card.select_one('a[href*="/jobs/view/"]')
        if not link:
            continue
        url = _schone_url(urljoin(BASIS, link.get("href", "")))
        if not url or url in gezien:
            continue

        titel = _tekst(card.select_one("h3.base-search-card__title, h3, a span[aria-hidden='true']"))
        if not titel:
            titel = _tekst(link)
        bedrijf = _tekst(card.select_one("h4.base-search-card__subtitle, .base-search-card__subtitle, .job-search-card__subtitle-link"))
        locatie = _tekst(card.select_one(".job-search-card__location, .base-search-card__metadata span"))
        datum_el = card.select_one("time")
        datum = datum_el.get("datetime", "") if datum_el else ""

        if not titel or len(titel) < 3:
            continue
        gezien.add(url)
        resultaat.append({
            "titel": titel,
            "bedrijf": bedrijf or "Onbekend bedrijf",
            "locatie": locatie or "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": datum,
            "bron": NAAM,
        })
    return resultaat


def _job_id(url):
    # LinkedIn-URL's zijn /jobs/view/{slug}-{id} of /jobs/view/{id}; het id is
    # de lange cijferreeks (meestal 10 cijfers), doorgaans achteraan.
    treffers = re.findall(r"\d{8,}", url or "")
    return treffers[-1] if treffers else ""


def _verrijk(vacatures, config):
    """Vul de omschrijving aan via de guest-detailendpoint, zodat LinkedIn-
    vacatures volwaardig scoren (hybride, salaris, inhoud) i.p.v. titel-only.

    Stopt netjes zodra LinkedIn blokkeert (429). detect_block_html staat uit:
    de detailpagina bevat login-prompts die anders een valse blokkade geven.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return
    sessie = _polite.PoliteSession(NAAM, {**config, "detect_block_html": False})
    limiet = int(config.get("max_detail_pages", 0))
    verrijkt = 0
    for v in vacatures:
        if verrijkt >= limiet:
            break
        jid = _job_id(v.get("url"))
        if not jid:
            continue
        try:
            html = sessie.get(DETAIL_URL + jid)
        except _polite.Geblokkeerd as blok:
            print(f"[LinkedIn] Detailverrijking gestopt ({blok}).")
            break
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")
        body = soup.select_one(".show-more-less-html__markup, .description__text")
        tekst = " ".join((body.get_text(" ", strip=True) if body else "").split())
        if tekst:
            v["omschrijving"] = tekst[:12000]
            verrijkt += 1
    if verrijkt:
        print(f"[LinkedIn] {verrijkt} detailpagina's verrijkt.")


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    gezien, resultaat = set(), []
    for html in htmls:
        for vacature in _parse(html):
            if vacature["url"] in gezien:
                continue
            gezien.add(vacature["url"])
            resultaat.append(vacature)
    resultaat = _polite.unieke_vacatures(resultaat)[: config.get("max_resultaten", 100)]
    print(f"[LinkedIn] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    if config.get("fetch_details"):
        _verrijk(resultaat, config)
    return resultaat
