"""Nette scraper voor Randstad — publieke vacaturezoekpagina's.

Volgt de regels in docs/source_policy.md. Standaard uitgeschakeld.
"""

from . import _polite

NAAM = "Randstad"
BASIS = "https://www.randstad.nl"
ZOEK_URL = "https://www.randstad.nl/vacatures/"


def _page_urls(config):
    zoek = config.get("base_url", ZOEK_URL)
    query = config.get("query", "")  # Randstad gebruikt de parameter 'zoekterm'.
    urls = []
    for p in range(1, min(int(config.get("max_pages", 2)), 2) + 1):
        params = []
        if query:
            params.append(f"zoekterm={query}")
        params.append(f"page={p}")
        urls.append(zoek + "?" + "&".join(params))
    return urls


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        # Alleen echte vacaturedetailpagina's: /vacatures/<id>/... (id is een getal).
        resultaat.extend(
            _polite.extraheer_vacatures(
                html, "/vacatures/", BASIS, NAAM, detail_regex=r"/vacatures/\d")
        )
    print(f"[Randstad] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
