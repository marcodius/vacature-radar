"""Nette scraper voor YoungCapital — publieke vacaturezoekpagina's.

Volgt de regels in docs/source_policy.md. Standaard uitgeschakeld.
"""

from . import _polite

NAAM = "YoungCapital"
BASIS = "https://www.youngcapital.nl"
ZOEK_URL = "https://www.youngcapital.nl/vacatures"


def _page_urls(config):
    zoek = config.get("base_url", ZOEK_URL)
    query = config.get("query", "")
    urls = []
    for p in range(1, min(int(config.get("max_pages", 2)), 2) + 1):
        params = []
        if query:
            params.append(f"q={query}")
        params.append(f"page={p}")
        urls.append(zoek + "?" + "&".join(params))
    return urls


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/vacature", BASIS, NAAM))
    print(f"[YoungCapital] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
