"""Generieke, gratis sitemap-provider.

Robots-conform alternatief voor betaalde scrape-diensten (zoals Apify): we lezen
vacature-URL's uit de officiele sitemap die een site zelf publiceert, en leiden
de titel af uit de URL-slug. Geen account, geen kosten, geen bot-detectie
omzeilen. Respecteert robots.txt, delay en caching via _polite.

Config (per bron in sources.json):
  "sitemap_url"   : URL van de sitemap of sitemap-index (verplicht).
  "detail_bevat"  : substring waaraan vacature-URL's moeten voldoen (bijv. "/vacature").
  "naam"          : weergavenaam voor de bron (bijv. "Werk.nl").
  "max_resultaten": maximum aantal vacatures.
"""

from . import _polite
from .. import relevance


def fetch(config):
    naam = config.get("naam") or config.get("_key", "Sitemap")
    sitemap_url = config.get("sitemap_url")
    detail_bevat = config.get("detail_bevat", "")
    max_res = config.get("max_resultaten", 50)
    land = config.get("country", "")
    # Werkgever-/gemeentesites: alle vacatures zitten op één plaats/werkgever.
    # Een vaste locatie/bedrijf garandeert correcte classificatie ook als de
    # detailpagina geen locatie in JSON-LD heeft.
    vaste_locatie = config.get("vaste_locatie")
    vast_bedrijf = config.get("vast_bedrijf")

    if not sitemap_url:
        print(f"[{naam}] Geen 'sitemap_url' in config. Bron wordt overgeslagen.")
        return []

    # Lees ruim in (de relevantiefilter knipt daarna fors), zodat we na het
    # filteren nog genoeg relevante vacatures overhouden.
    filter_aan, trefwoorden = relevance.filter_config(config)
    scan_factor = int(config.get("relevance_scan_factor", 15))
    lees_limiet = max_res * scan_factor if filter_aan else max_res
    urls = _polite.lees_sitemap_urls(
        sitemap_url, naam, config, bevat=detail_bevat, max_urls=lees_limiet
    )

    if filter_aan:
        totaal = len(urls)
        urls = [u for u in urls if relevance.is_relevant(u, trefwoorden=trefwoorden)]
        print(f"[{naam}] {len(urls)} van {totaal} sitemap-URL's relevant na voorfilter.")
    urls = urls[:max_res]

    resultaat = []
    # JS-gerenderde bronnen (bijv. NVB) verrijken we via een headless browser;
    # andere bronnen via een gewone HTTP-sessie.
    if config.get("render_js"):
        from . import _browser
        sessie = _browser.BrowserRenderer(naam, config)
    else:
        sessie = _polite.PoliteSession(naam, config)
    detail_limiet = int(config.get("max_detail_pages", 0))
    verrijkt_aantal = 0
    for url in urls:
        vacature = {
            "titel": _polite.titel_uit_slug(url),
            "bedrijf": vast_bedrijf or "Onbekend bedrijf",
            "locatie": vaste_locatie or "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": "",
            "bron": naam,
            "land": land,
        }
        if config.get("fetch_details") and verrijkt_aantal < detail_limiet:
            vacature = _polite.verrijk_met_detailpagina(vacature, sessie)
            verrijkt_aantal += 1
        # Vaste locatie/bedrijf is gezaghebbend voor werkgever-sites.
        if vaste_locatie:
            vacature["locatie"] = vaste_locatie
        if vast_bedrijf:
            vacature["bedrijf"] = vast_bedrijf
        resultaat.append(vacature)
    if hasattr(sessie, "close"):
        sessie.close()
    resultaat = _polite.unieke_vacatures(resultaat)
    print(f"[{naam}] {len(resultaat)} vacatures via sitemap "
          f"({verrijkt_aantal} verrijkt met detailpagina).")
    return resultaat
