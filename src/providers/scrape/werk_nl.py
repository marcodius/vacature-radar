"""Nette scraper voor Werk.nl (UWV) — publieke vacaturezoekpagina's.

Volgt de regels in docs/source_policy.md (robots.txt, max 2 pagina's, 10s delay,
caching, stop bij blokkade, geen stealth/login). Standaard uitgeschakeld.
"""

from . import _polite

NAAM = "Werk.nl"
BASIS = "https://www.werk.nl"
ZOEK_URL = "https://www.werk.nl/werk_nl/werknemer/vacatures"


def _page_urls(config):
    query = config.get("query", "")
    pagina_param = "&pagina={}" if "?" in ZOEK_URL else "?pagina={}"
    urls = []
    for p in range(1, min(int(config.get("max_pages", 2)), 2) + 1):
        url = ZOEK_URL + (f"?zoekterm={query}" if query else "") + pagina_param.format(p)
        urls.append(url)
    return urls


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/vacature", BASIS, NAAM))
    print(f"[Werk.nl] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
