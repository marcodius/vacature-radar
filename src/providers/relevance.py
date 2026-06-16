"""Gedeelde relevantiefilter voor brede bronnen (sitemaps, lijst-scrapers, RSS).

Sitemaps en lijst-scrapers leveren vacatures uit ALLE sectoren (chauffeur,
productiemedewerker, verpleegkundige, ...). Voor Kevins profiel is daarvan maar
een klein deel relevant. Door vroeg te filteren op vakgebied-trefwoorden:

- valt de junk-flood weg (minder onterechte afwijzingen in de scoringsstap);
- gaat het beperkte detail-ophaalbudget naar relevante vacatures;
- draait de pijplijn sneller.

Dit is GEEN scoring. Het is een grove voorfilter op titel/URL. De echte
beoordeling (salaris, hybride, locatie, dealbreakers) gebeurt in score_jobs.py.
Per bron uit te zetten met "filter_relevant": false en te overschrijven met
"relevance_keywords": [...] in config/sources.json.
"""

import re

# Brede vakgebied-trefwoorden, afgeleid van het profiel (titels + werkzaamheden).
# Bewust ruim: liever een paar twijfelgevallen erbij dan een goede missen; de
# scoringsstap filtert daarna alsnog streng.
STANDAARD_TREFWOORDEN = [
    "crm", "salesforce", "hubspot",
    "revenue operations", "revops", "sales operations", "sales support",
    "salessupport", "business operations", "customer operations",
    "customer success", "customer experience", "business development",
    "account manager", "accountmanager", "account support",
    "commercieel", "commercie", "binnendienst",
    "operations", "operationeel",
    "procesoptimalisatie", "procesverbetering", "proces coordinator",
    "procescoordinator", "procescoördinator",
    "projectcoordinator", "projectcoördinator", "project coordinator",
    "projectondersteuning", "project support",
    "implementatie", "implementation",
    "data-analist", "data analist", "data-analyse", "dataanalyse",
    "rapportage", "klantproces", "membership", "community operations",
    "business support", "sales", "marketing operations",
]


def _normaliseer(tekst):
    """Maak slug/URL/titel vergelijkbaar: scheidingstekens -> spatie, lowercase."""
    laag = (tekst or "").lower()
    return re.sub(r"[-_/]+", " ", laag)


def is_relevant(*teksten, trefwoorden=None):
    """True als een van de teksten een vakgebied-trefwoord bevat."""
    woorden = trefwoorden if trefwoorden is not None else STANDAARD_TREFWOORDEN
    samen = " ".join(_normaliseer(t) for t in teksten)
    return any(tw.lower() in samen for tw in woorden)


def filter_config(config):
    """Lees relevantie-instellingen uit een bron-config.

    Geeft (aan, trefwoorden) terug. 'aan' staat standaard aan; per bron uit te
    zetten met "filter_relevant": false.
    """
    aan = config.get("filter_relevant", True)
    trefwoorden = config.get("relevance_keywords") or None
    return aan, trefwoorden
