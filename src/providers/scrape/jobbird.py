"""Nette scraper voor Jobbird.

Belangrijk: Jobbird verbiedt in robots.txt de zoekpagina's met queryparameters
(`Disallow: /nl/vacature?*`). Die crawlen we dus NIET. De robots-conforme route
is de officiele sitemap (staat in robots.txt) -> vacaturedetail-URL's; de titel
leiden we af uit de URL-slug.

Twee standen:
- mode "sitemap" (standaard): lees vacature-URL's uit de sitemap.
- mode "search": probeer de zoekpagina (wordt door robots geblokkeerd; alleen
  zinvol als Jobbird zijn robots-beleid wijzigt).
Volgt verder de regels in docs/source_policy.md. Standaard uitgeschakeld.
"""

from . import _polite
from .. import relevance

NAAM = "Jobbird"
BASIS = "https://www.jobbird.com"
SITEMAP_INDEX = "https://www.jobbird.com/nl/sitemaps/index.xml"
ZOEK_URL = "https://www.jobbird.com/nl/vacature/"


def _search_page_urls(config):
    return _polite.bouw_zoek_urls(
        config.get("base_url", ZOEK_URL), config, "s", page_param="page", page_start=1
    )


def _via_sitemap(config):
    max_res = config.get("max_resultaten", 50)
    land = config.get("country", "")
    filter_aan, trefwoorden = relevance.filter_config(config)
    scan_factor = int(config.get("relevance_scan_factor", 15))
    lees_limiet = max_res * scan_factor if filter_aan else max_res
    urls = _polite.lees_sitemap_urls(
        config.get("sitemap_url", SITEMAP_INDEX), NAAM, config,
        bevat="/nl/vacature/", max_urls=lees_limiet,
    )
    if filter_aan:
        totaal = len(urls)
        urls = [u for u in urls if relevance.is_relevant(u, trefwoorden=trefwoorden)]
        print(f"[Jobbird] {len(urls)} van {totaal} sitemap-URL's relevant na voorfilter.")
    urls = urls[:max_res]

    resultaat = []
    sessie = _polite.PoliteSession(NAAM, config)
    detail_limiet = int(config.get("max_detail_pages", 0))
    verrijkt_aantal = 0
    for url in urls:
        vacature = {
            "titel": _polite.titel_uit_slug(url),
            "bedrijf": "Onbekend bedrijf",
            "locatie": "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": "",
            "bron": NAAM,
            "land": land,
        }
        if config.get("fetch_details") and verrijkt_aantal < detail_limiet:
            vacature = _polite.verrijk_met_detailpagina(vacature, sessie)
            verrijkt_aantal += 1
        resultaat.append(vacature)
    print(f"[Jobbird] {len(resultaat)} vacatures via sitemap "
          f"({verrijkt_aantal} verrijkt met detailpagina).")
    return resultaat


def _via_search(config):
    htmls = _polite.haal_pagina_html(NAAM, _search_page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/nl/vacature/", BASIS, NAAM))
    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[Jobbird] {len(resultaat)} vacatures uit {len(htmls)} zoekpagina('s).")
    return resultaat[: config.get("max_resultaten", 50)]


def fetch(config):
    if config.get("mode", "sitemap") == "search":
        return _via_search(config)
    return _via_sitemap(config)
