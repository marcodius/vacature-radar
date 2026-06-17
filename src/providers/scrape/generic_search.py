"""Generieke HTML-zoekprovider voor vacaturebanken met simpele zoekpagina's.

Config stuurt URL-opbouw en linkextractie:
  "naam"          : weergavenaam.
  "base_url"      : zoekpagina.
  "query_param"   : queryparameter voor zoekterm.
  "location_param": queryparameter voor locatie (optioneel).
  "page_param"    : queryparameter voor pagina (optioneel).
  "page_start"    : eerste paginawaarde (standaard 1).
  "page_step"     : stap per pagina (standaard 1).
  "detail_bevat"  : substring die vacaturedetail-links moeten bevatten.
  "basis_url"     : basis voor relatieve links.
"""

from . import _polite
from .. import relevance


def _page_urls(config):
    extra = config.get("extra_params", {})
    return _polite.bouw_zoek_urls(
        config["base_url"],
        config,
        config.get("query_param", "q"),
        location_param=config.get("location_param"),
        page_param=config.get("page_param", "page"),
        page_start=int(config.get("page_start", 1)),
        page_step=int(config.get("page_step", 1)),
        extra_params=extra,
    )


def fetch(config):
    naam = config.get("naam") or config.get("_key", "Generic")
    if not config.get("base_url"):
        print(f"[{naam}] Geen 'base_url' in config. Bron wordt overgeslagen.")
        return []
    detail_bevat = config.get("detail_bevat", "/vacature")
    basis_url = config.get("basis_url") or config.get("base_url")

    land = config.get("country", "")
    # JS-gerenderde lijsten (SPA's zoals werkenbij.amsterdam.nl) via headless browser.
    if config.get("render_js"):
        from . import _browser
        sessie = _browser.BrowserRenderer(naam, config)
        htmls = [h for h in (sessie.get(u) for u in _page_urls(config)) if h]
        sessie.close()
    else:
        htmls = _polite.haal_pagina_html(naam, _page_urls(config), config)
    resultaat = []
    for html in htmls:
        resultaat.extend(
            _polite.extraheer_vacatures(
                html,
                detail_bevat,
                basis_url,
                naam,
                detail_regex=config.get("detail_regex"),
            )
        )

    resultaat = _polite.unieke_vacatures(resultaat)
    vaste_locatie = config.get("vaste_locatie")
    vast_bedrijf = config.get("vast_bedrijf")
    for v in resultaat:
        if land:
            v.setdefault("land", land)
        if vaste_locatie:
            v["locatie"] = vaste_locatie
        if vast_bedrijf:
            v["bedrijf"] = vast_bedrijf

    filter_aan, trefwoorden = relevance.filter_config(config)
    if filter_aan:
        totaal = len(resultaat)
        resultaat = [
            v for v in resultaat
            if relevance.is_relevant(v.get("titel", ""), v.get("url", ""),
                                     trefwoorden=trefwoorden)
        ]
        print(f"[{naam}] {len(resultaat)} van {totaal} vacatures relevant na voorfilter "
              f"(uit {len(htmls)} pagina's).")
    else:
        print(f"[{naam}] {len(resultaat)} vacatures uit {len(htmls)} pagina('s).")
    return resultaat[: config.get("max_resultaten", 100)]
