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

NAAM = "Jobbird"
BASIS = "https://www.jobbird.com"
SITEMAP_INDEX = "https://www.jobbird.com/nl/sitemaps/index.xml"
ZOEK_URL = "https://www.jobbird.com/nl/vacature/"


def _search_page_urls(config):
    zoek = config.get("base_url", ZOEK_URL)
    query = config.get("query", "")
    urls = []
    for p in range(1, min(int(config.get("max_pages", 2)), 2) + 1):
        params = [f"s={query}"] if query else []
        params.append(f"page={p}")
        urls.append(zoek + "?" + "&".join(params))
    return urls


def _via_sitemap(config):
    max_res = config.get("max_resultaten", 50)
    urls = _polite.lees_sitemap_urls(
        config.get("sitemap_url", SITEMAP_INDEX), NAAM, config,
        bevat="/nl/vacature/", max_urls=max_res,
    )
    resultaat = []
    for url in urls:
        resultaat.append({
            "titel": _polite.titel_uit_slug(url),
            "bedrijf": "Onbekend bedrijf",
            "locatie": "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": "",
            "bron": NAAM,
        })
    print(f"[Jobbird] {len(resultaat)} vacatures via sitemap.")
    return resultaat


def _via_search(config):
    htmls = _polite.haal_pagina_html(NAAM, _search_page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/nl/vacature/", BASIS, NAAM))
    print(f"[Jobbird] {len(resultaat)} vacatures uit {len(htmls)} zoekpagina('s).")
    return resultaat[: config.get("max_resultaten", 50)]


def fetch(config):
    if config.get("mode", "sitemap") == "search":
        return _via_search(config)
    return _via_sitemap(config)
