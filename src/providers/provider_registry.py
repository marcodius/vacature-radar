"""Centrale registratie van alle vacaturebronnen.

Koppelt de bronsleutel uit config/sources.json aan de provider-module die
`fetch(config) -> list[dict]` aanbiedt. Zo blijft fetch_jobs.py bronnen-
onafhankelijk en voeg je een bron toe door hier één regel toe te voegen.

Drie typen bronnen:
- "api"            : officiele API's (sleutel via environment variables).
- "polite_scrape"  : configureerbare scrapers (zie docs/source_policy.md).
- "manual"         : handmatige fallback-import (bijv. LinkedIn, Indeed).
"""

from providers import arbeitnow, ats, jobicy, rss
from providers.api import adzuna, jooble, nationale_vacaturebank, vacatures_overheid
from providers.manual import manual_links
from providers.scrape import (
    generic_search,
    indeed,
    jobbird,
    linkedin,
    randstad,
    sitemap_source,
    werk_nl,
    youngcapital,
)

# bronsleutel -> module met fetch(config)
REGISTRY = {
    # API-bronnen
    "nationale_vacaturebank": nationale_vacaturebank,
    "vacatures_overheid": vacatures_overheid,
    "jooble": jooble,
    "adzuna": adzuna,
    # Extra gratis API-bronnen (geen sleutel)
    "arbeitnow": arbeitnow,
    "jobicy": jobicy,
    "rss": rss,
    "ats_bedrijven": ats,
    # Scrape-bronnen
    "werk_nl": werk_nl,
    "jobbird": jobbird,
    "randstad": randstad,
    "youngcapital": youngcapital,
    "linkedin": linkedin,
    "indeed": indeed,
    "generic_search": generic_search,
    # Gratis sitemap-bronnen
    "werk_nl_sitemap": sitemap_source,
    "nationale_vacaturebank_sitemap": sitemap_source,
    "werkenvoornederland_sitemap": sitemap_source,
    "werkenbijdeoverheid": sitemap_source,
    "gemeente_utrecht": sitemap_source,
    "gemeente_ede": sitemap_source,
    "gemeente_amsterdam": generic_search,
    "academictransfer": sitemap_source,
    "tempo_team": sitemap_source,
    "magnet_me": sitemap_source,
    "intermediair": generic_search,
    "talent": generic_search,
    "jobrapido": generic_search,
    "simplyhired": generic_search,
    "joblift": generic_search,
    # Handmatige fallback-bronnen (LinkedIn/Indeed) — beide via manual_links
    "linkedin_manual": manual_links,
    "indeed_manual": manual_links,
}


def get_provider(bron_key):
    """Geef de provider-module voor een bronsleutel, of None."""
    return REGISTRY.get(bron_key)
