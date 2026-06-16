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


def fetch(config):
    naam = config.get("naam") or config.get("_key", "Sitemap")
    sitemap_url = config.get("sitemap_url")
    detail_bevat = config.get("detail_bevat", "")
    max_res = config.get("max_resultaten", 50)

    if not sitemap_url:
        print(f"[{naam}] Geen 'sitemap_url' in config. Bron wordt overgeslagen.")
        return []

    urls = _polite.lees_sitemap_urls(
        sitemap_url, naam, config, bevat=detail_bevat, max_urls=max_res
    )
    resultaat = [{
        "titel": _polite.titel_uit_slug(u),
        "bedrijf": "Onbekend bedrijf",
        "locatie": "Nederland",
        "url": u,
        "omschrijving": "",
        "datum": "",
        "bron": naam,
    } for u in urls]
    print(f"[{naam}] {len(resultaat)} vacatures via sitemap.")
    return resultaat
