"""Scraper voor publieke LinkedIn vacaturezoekresultaten.

Gebruikt de publieke guest jobs endpoint. Deze provider gebruikt geen login,
cookies, sessietokens of browser-automation; blokkades worden door _polite
netjes afgevangen.
"""

import re
import time
from urllib.parse import urlencode, urljoin, urlparse, urlunparse

from . import _polite

NAAM = "LinkedIn"
BASIS = "https://www.linkedin.com"
ZOEK_URL = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
# Guest-endpoint met de volledige vacaturetekst (geen login nodig).
DETAIL_URL = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/"
# Kernwoorden om het (mogelijk krappe) verrijkingsbudget eerst aan de kansrijkste
# titels te besteden vóór een eventuele 429.
DETAIL_KERN_STERK = [
    "crm", "salesforce", "hubspot", "binnendienst", "sales support",
    "customer success", "operations specialist", "revenue operations",
    "sales operations", "implementatie",
]


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


def _detail_prioriteit(vacature):
    """0 voor titels met een sterk kernwoord (eerst verrijken), anders 1."""
    titel = (vacature.get("titel") or "").lower()
    return 0 if any(kw in titel for kw in DETAIL_KERN_STERK) else 1


def _verrijk(vacatures, config):
    """Vul de omschrijving aan via de guest-detailendpoint, zodat LinkedIn-
    vacatures volwaardig scoren (hybride, salaris, inhoud) i.p.v. titel-only.

    De detailendpoint kent een korte burst-rate-limit: bij ~0.2s tussenpozen
    429't hij na ~8 calls, maar bij een rustige delay (~2s) gaan tientallen calls
    goed, en een 429 is een korte cooldown die na ~15s herstelt. Daarom: aparte
    detail-delay, en bij 429 backoff + retry i.p.v. direct volledig stoppen. De
    kansrijkste titels gaan eerst, zodat een krap budget goed wordt besteed.
    detect_block_html staat uit (de detailpagina bevat login-prompts).
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return
    detail_delay = float(config.get("detail_delay_seconds", 2.0))
    backoff = float(config.get("detail_backoff_seconds", 15))
    sessie = _polite.PoliteSession(
        NAAM, {**config, "detect_block_html": False, "delay_seconds": detail_delay})
    limiet = int(config.get("max_detail_pages", 0))

    kandidaten = sorted(
        [v for v in vacatures if _job_id(v.get("url"))], key=_detail_prioriteit)
    verrijkt = mislukt_op_rij = 0
    for v in kandidaten:
        if verrijkt >= limiet:
            break
        jid = _job_id(v.get("url"))
        html = None
        for poging in range(2):  # normale poging + één na backoff
            try:
                html = sessie.get(DETAIL_URL + jid)
                break
            except _polite.Geblokkeerd:
                if poging == 0:
                    time.sleep(backoff)  # korte cooldown, geen harde blokkade
        if html is None:
            mislukt_op_rij += 1
            if mislukt_op_rij >= 2:
                print("[LinkedIn] Detailverrijking gestopt (herhaald 429 na backoff).")
                break
            continue
        mislukt_op_rij = 0
        body = BeautifulSoup(html, "html.parser").select_one(
            ".show-more-less-html__markup, .description__text")
        tekst = " ".join((body.get_text(" ", strip=True) if body else "").split())
        if tekst:
            v["omschrijving"] = tekst[:12000]
            verrijkt += 1
    if verrijkt:
        print(f"[LinkedIn] {verrijkt} detailpagina's verrijkt.")


def _haal_lijst(config):
    """Haal de zoekresultaatpagina's met backoff i.p.v. hard stoppen bij 429.

    De lijst-endpoint (seeMoreJobPostings) 429't bij snelle bursts (delay 0.2);
    met een rustigere delay + backoff/retry halen we veel meer pagina's binnen
    vóór een eventuele harde blokkade. Stopt pas na herhaalde 429 op rij."""
    sessie = _polite.PoliteSession(NAAM, config)
    backoff = float(config.get("list_backoff_seconds", 15))
    urls = _page_urls(config)
    max_fetch = int(config.get("max_fetch_pages", len(urls)))
    htmls, mislukt_op_rij = [], 0
    for url in urls[:max_fetch]:
        html = None
        for poging in range(2):  # normale poging + één na backoff
            try:
                html = sessie.get(url)
                break
            except _polite.Geblokkeerd:
                if poging == 0:
                    time.sleep(backoff)
        if html is None:
            mislukt_op_rij += 1
            if mislukt_op_rij >= 2:
                print("[LinkedIn] Lijst-ophalen gestopt (herhaald 429 na backoff).")
                break
            continue
        mislukt_op_rij = 0
        htmls.append(html)
    return htmls


def fetch(config):
    htmls = _haal_lijst(config)
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
