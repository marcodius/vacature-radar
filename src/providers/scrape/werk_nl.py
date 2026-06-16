"""Nette scraper voor Werk.nl (UWV) — publieke vacaturezoekpagina's.

Volgt de regels in docs/source_policy.md (robots.txt, max 2 pagina's, 10s delay,
caching, stop bij blokkade, geen stealth/login). Standaard uitgeschakeld.
"""

from urllib.parse import urlencode

from . import _polite

NAAM = "Werk.nl"
BASIS = "https://www.werk.nl"
ZOEK_URL = "https://www.werk.nl/werk_nl/werknemer/vacatures"


def _page_urls(config):
    urls = []
    for query in _polite.lijst_config(config, "query", "queries", "") or [""]:
        for p in range(1, int(config.get("max_pages", 2)) + 1):
            params = {"pagina": p}
            if query:
                params["zoekterm"] = query
            urls.append(ZOEK_URL + "?" + urlencode(params))
    return urls


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/vacature", BASIS, NAAM))
    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[Werk.nl] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
