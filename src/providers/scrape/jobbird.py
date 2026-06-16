"""Nette scraper voor Jobbird — publieke vacaturezoekpagina.

Gebruikt uitsluitend https://www.jobbird.com/nl/vacature/ (NIET career.jobbird.com).
Volgt de regels in docs/source_policy.md. Standaard uitgeschakeld.
"""

from . import _polite

NAAM = "Jobbird"
BASIS = "https://www.jobbird.com"
STANDAARD_ZOEK = "https://www.jobbird.com/nl/vacature/"


def _page_urls(config):
    zoek = config.get("base_url", STANDAARD_ZOEK)
    query = config.get("query", "")
    urls = []
    for p in range(1, min(int(config.get("max_pages", 2)), 2) + 1):
        params = []
        if query:
            params.append(f"s={query}")
        params.append(f"page={p}")
        urls.append(zoek + ("?" + "&".join(params) if params else ""))
    return urls


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/nl/vacature/", BASIS, NAAM))
    print(f"[Jobbird] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
