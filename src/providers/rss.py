"""Generieke RSS-provider.

Leest vacatures uit officiele RSS- of Atom-feeds die boards zelf aanbieden.
Dit is GEEN scraping: je gebruikt de feed die de bron bewust publiceert.

Feeds zet je in config/sources.json onder 'rss':

  "rss": {
    "aan": true,
    "max_resultaten": 50,
    "feeds": [
      {"naam": "Voorbeeldboard", "url": "https://voorbeeld.nl/vacatures/rss"}
    ]
  }

Elke feed-entry wordt omgezet naar het standaard vacatureformaat. Niet elke feed
bevat 'bedrijf' of 'locatie'; ontbrekende velden worden 'Onbekend'.
"""

import feedparser

NAAM = "RSS"


def _normaliseer(entry, bron_naam):
    omschrijving = entry.get("summary") or entry.get("description") or ""
    datum = ""
    if entry.get("published"):
        datum = entry.get("published", "")[:16]
    elif entry.get("updated"):
        datum = entry.get("updated", "")[:16]

    return {
        "titel": entry.get("title") or "Onbekende functie",
        # Veel feeds zetten het bedrijf in 'author'; anders onbekend.
        "bedrijf": entry.get("author") or "Onbekend bedrijf",
        "locatie": entry.get("location") or "Onbekend",
        "url": entry.get("link") or "",
        "omschrijving": omschrijving,
        "datum": datum,
        "bron": f"{NAAM}: {bron_naam}" if bron_naam else NAAM,
    }


def fetch(config):
    """Haal vacatures op uit alle opgegeven feeds. config = 'rss'-blok."""
    max_resultaten = config.get("max_resultaten", 50)
    feeds = config.get("feeds", [])

    if not feeds:
        print("[RSS] Geen feeds opgegeven in config. Bron wordt overgeslagen.")
        return []

    resultaat = []
    for feed in feeds:
        url = feed.get("url")
        bron_naam = feed.get("naam", "")
        if not url:
            continue
        # Sla nog niet-ingevulde placeholder-URL's netjes over.
        if not url.lower().startswith("http") or "plaats_hier" in url.lower():
            print(f"[RSS] Feed '{bron_naam}' heeft nog geen echte URL ingevuld. Overslaan.")
            continue
        try:
            geparset = feedparser.parse(url)
            if getattr(geparset, "bozo", False) and not geparset.entries:
                print(f"[RSS] Feed '{bron_naam or url}' kon niet gelezen worden. Overslaan.")
                continue
            for entry in geparset.entries:
                resultaat.append(_normaliseer(entry, bron_naam))
            print(f"[RSS] {len(geparset.entries)} items uit '{bron_naam or url}'.")
        except Exception as fout:  # noqa: BLE001
            print(f"[RSS] Feed '{bron_naam or url}' mislukt: {fout}. Overslaan.")

    return resultaat[:max_resultaten]
