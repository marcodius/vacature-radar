"""Centrale registratie van alle vacaturebronnen.

Koppelt de bronsleutel uit config/sources.json aan de provider-module die
`fetch(config) -> list[dict]` aanbiedt. Zo blijft fetch_jobs.py bronnen-
onafhankelijk en voeg je een bron toe door hier één regel toe te voegen.

Drie typen bronnen:
- "api"            : officiele API's (sleutel via environment variables).
- "polite_scrape"  : nette, beperkte scrapers (zie docs/source_policy.md).
- "manual"         : handmatige import (LinkedIn, Indeed) — nooit scrapen.
"""

from providers.api import adzuna, jooble, nationale_vacaturebank, vacatures_overheid
from providers.manual import manual_links
from providers.scrape import jobbird, randstad, werk_nl, youngcapital

# bronsleutel -> module met fetch(config)
REGISTRY = {
    # API-bronnen
    "nationale_vacaturebank": nationale_vacaturebank,
    "vacatures_overheid": vacatures_overheid,
    "jooble": jooble,
    "adzuna": adzuna,
    # Polite scrape-bronnen
    "werk_nl": werk_nl,
    "jobbird": jobbird,
    "randstad": randstad,
    "youngcapital": youngcapital,
    # Manual-only bronnen (LinkedIn/Indeed) — beide via manual_links
    "linkedin_manual": manual_links,
    "indeed_manual": manual_links,
}


def get_provider(bron_key):
    """Geef de provider-module voor een bronsleutel, of None."""
    return REGISTRY.get(bron_key)
