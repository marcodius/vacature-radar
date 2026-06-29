"""Indeed-provider via headless browser.

Statische requests naar Indeed worden geblokkeerd (Cloudflare/anti-bot, HTTP 403
op álle endpoints incl. RSS). Een echte browser (Playwright) krijgt de
zoekresultaatpagina wél; daarin zit een ingebed JSON-blok
(`window.mosaic.providerData["mosaic-provider-jobcards"]`) met titel, bedrijf,
locatie, jobkey en soms salaris. Dat parsen we — veel robuuster dan DOM-scrapen.

LET OP: Indeed blokkeert datacenter-IP's (zoals GitHub Actions-runners) actiever
dan residentiële IP's. Deze provider is daarom best-effort: bij een blokkade of
ontbrekend JSON-blok levert hij netjes 0 vacatures (geen crash). De DOM-parser
blijft als fallback. Gebruikt geen login of cookies.

Optionele proxy-route (voor CI): als de env var INDEED_PROXY_KEY aanwezig is én
"proxy": true in de config staat, lopen de zoekpagina's via een scraping-/proxy-
API met residentieel IP + JS-rendering (bijv. ScraperAPI met render=true). De
response is dezelfde gerenderde HTML, dus dezelfde mosaic-parser werkt. Zonder de
env var valt hij terug op de directe headless browser (huidig gedrag, vaak 0 in
CI). Geen sleutel in code; alleen via Secret/environment.
"""

import json
import os
import re
from urllib.parse import parse_qs, quote_plus, urlencode, urljoin, urlparse

import requests

from . import _browser, _polite
from .. import relevance

NAAM = "Indeed"
DEFAULT_PROXY_ENDPOINT = "https://api.scraperapi.com/?api_key={key}&render=true&url={url}"
BASIS = "https://nl.indeed.com"
ZOEK_URL = "https://nl.indeed.com/jobs"

_MOSAIC_RE = re.compile(r'mosaic-provider-jobcards"\]\s*=\s*(\{.*?\});', re.S)


def _page_urls(config):
    urls = []
    queries = _polite.lijst_config(config, "query", "queries", "crm")
    locaties = _polite.lijst_config(config, "location", "locations", config.get("locatie", "Nederland"))
    for query in queries:
        for locatie in (locaties or ["Nederland"]):
            for p in range(0, int(config.get("max_pages", 1))):
                params = {"q": query, "l": locatie, "start": p * 10}
                if config.get("radius") is not None:
                    params["radius"] = str(config["radius"])
                urls.append(config.get("base_url", ZOEK_URL) + "?" + urlencode(params))
    return urls


def _strip_html(tekst):
    return re.sub(r"<[^>]+>", " ", tekst or "").replace("&nbsp;", " ").strip()


def _parse_mosaic(html):
    """Parse het ingebedde jobcards-JSON. Geeft [] als het er niet is."""
    match = _MOSAIC_RE.search(html)
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
    except Exception:  # noqa: BLE001
        return []
    results = (data.get("metaData", {})
                   .get("mosaicProviderJobCardsModel", {})
                   .get("results") or [])
    resultaat = []
    for r in results:
        jobkey = r.get("jobkey")
        if not jobkey:
            continue
        salaris = ""
        snippet = r.get("salarySnippet") or r.get("estimatedSalary") or {}
        if isinstance(snippet, dict) and snippet.get("text"):
            salaris = " Salaris: " + snippet["text"] + "."
        omschrijving = (_strip_html(r.get("snippet") or "") + salaris).strip()
        resultaat.append({
            "titel": r.get("title") or "Onbekende functie",
            "bedrijf": r.get("company") or "Onbekend bedrijf",
            "locatie": r.get("formattedLocation") or "Nederland",
            "url": f"{BASIS}/viewjob?jk={jobkey}",
            "omschrijving": omschrijving,
            "datum": "",
            "bron": NAAM,
            "land": "NL",
        })
    return resultaat


def _tekst(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def _parse_dom(html):
    """Fallback: scrape de DOM als het JSON-blok ontbreekt."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return []
    soup = BeautifulSoup(html, "html.parser")
    resultaat, gezien = [], set()
    for card in soup.select("div.job_seen_beacon, div[data-jk], td.resultContent"):
        link = card.select_one('a[href*="/viewjob"], a[href*="/rc/clk"], a[data-jk]')
        titel_el = card.select_one("h2.jobTitle span[title], h2.jobTitle span, a span[title]")
        titel = (titel_el.get("title") if titel_el and titel_el.get("title") else _tekst(titel_el))
        if not titel and link:
            titel = _tekst(link)
        jk = ""
        for el in (card, link):
            if el and el.get("data-jk"):
                jk = el.get("data-jk")
                break
        if not jk and link:
            jk = (parse_qs(urlparse(link.get("href", "")).query).get("jk") or [""])[0]
        url = f"{BASIS}/viewjob?jk={jk}" if jk else (urljoin(BASIS, link.get("href", "")) if link else "")
        if not titel or not url or url in gezien:
            continue
        gezien.add(url)
        resultaat.append({
            "titel": titel,
            "bedrijf": _tekst(card.select_one('[data-testid="company-name"], .companyName')) or "Onbekend bedrijf",
            "locatie": _tekst(card.select_one('[data-testid="text-location"], .companyLocation')) or "Nederland",
            "url": url,
            "omschrijving": _tekst(card.select_one('.job-snippet, [data-testid="jobsnippet"]')),
            "datum": "",
            "bron": NAAM,
            "land": "NL",
        })
    return resultaat


def _proxy_get(url, api_key, config):
    """Haal de Indeed-zoekpagina via een scraping-/proxy-API (residentieel IP +
    JS-render). Geeft gerenderde HTML of None."""
    endpoint = config.get("proxy_endpoint", DEFAULT_PROXY_ENDPOINT)
    req_url = endpoint.format(key=api_key, url=quote_plus(url))
    try:
        resp = requests.get(req_url, timeout=int(config.get("proxy_timeout", 90)))
        if resp.status_code == 200 and resp.text:
            return resp.text
        print(f"[{NAAM}] Proxy HTTP {resp.status_code} voor zoekpagina.")
    except Exception as fout:  # noqa: BLE001
        print(f"[{NAAM}] Proxy-request mislukt: {fout}.")
    return None


def fetch(config):
    # Optionele proxy-route (secret-gated); anders de directe headless browser.
    proxy_key = os.environ.get(config.get("proxy_key_env", "INDEED_PROXY_KEY"))
    gebruik_proxy = bool(proxy_key) and config.get("proxy", False)
    renderer = None
    if not gebruik_proxy:
        config = {**config, "render_wait": config.get("render_wait", "domcontentloaded")}
        renderer = _browser.BrowserRenderer(NAAM, config)

    gezien, resultaat = set(), []
    paginas, met_data = 0, 0
    for url in _page_urls(config):
        html = _proxy_get(url, proxy_key, config) if gebruik_proxy else renderer.get(url)
        if not html:
            continue
        paginas += 1
        rijen = _parse_mosaic(html) or _parse_dom(html)
        if rijen:
            met_data += 1
        for v in rijen:
            if v["url"] in gezien:
                continue
            gezien.add(v["url"])
            resultaat.append(v)
    if renderer is not None and hasattr(renderer, "close"):
        renderer.close()

    filter_aan, trefwoorden = relevance.filter_config(config)
    if filter_aan:
        resultaat = [v for v in resultaat
                     if relevance.is_relevant(v["titel"], v["url"], trefwoorden=trefwoorden)]

    if paginas and not met_data:
        print(f"[{NAAM}] {paginas} pagina's geladen maar geen job-data "
              f"(waarschijnlijk geblokkeerd op dit IP). 0 vacatures.")
    else:
        print(f"[{NAAM}] {len(resultaat)} vacatures uit {paginas} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
