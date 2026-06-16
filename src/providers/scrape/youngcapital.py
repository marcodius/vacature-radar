"""Nette scraper voor YoungCapital — publieke vacaturezoekpagina's.

Volgt de regels in docs/source_policy.md. Standaard uitgeschakeld.
"""

from . import _polite

NAAM = "YoungCapital"
BASIS = "https://www.youngcapital.nl"
ZOEK_URL = "https://www.youngcapital.nl/vacatures"


def _page_urls(config):
    return _polite.bouw_zoek_urls(
        config.get("base_url", ZOEK_URL), config, "q", page_param="page", page_start=1
    )


def fetch(config):
    htmls = _polite.haal_pagina_html(NAAM, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(_polite.extraheer_vacatures(html, "/vacature", BASIS, NAAM))
    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[YoungCapital] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
