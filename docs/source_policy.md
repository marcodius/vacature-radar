# Bronbeleid — Vacature Radar

Doel: maximale Nederlandse vacaturedekking. Elke vacaturebron mag via API,
sitemap, RSS, statische HTML of een andere scraper-route worden aangesloten,
zolang de bron publiek bereikbare vacature-informatie aanbiedt.

## Bronnen en methode

| Bron | Meenemen? | Methode |
| --- | --- | --- |
| Nationale Vacaturebank | Ja | API of scrape/sitemap |
| Vacatures Overheid (CSO) | Ja | API of scrape/sitemap |
| Jooble NL | Ja | API of scrape/sitemap |
| Adzuna NL | Ja | API of scrape/sitemap |
| Werk.nl | Ja | Scrape of sitemap |
| Jobbird (`jobbird.com/nl/vacature/`) | Ja | Scrape of sitemap |
| Randstad | Ja | Scrape |
| YoungCapital | Ja | Scrape of sitemap |
| LinkedIn | Ja | Scrape of handmatige import |
| Indeed | Ja | Scrape of handmatige import |
| Andere vacaturesites | Ja | Scrape, sitemap, RSS of API |

API-sleutels staan nooit in de code; alleen in environment variables /
GitHub Secrets.

## Scraping-uitgangspunt

Scraping is een ondersteunde bronroute voor alle sites met publiek toegankelijke
vacaturepagina's. Gebruik bij voorkeur de route die de meeste bruikbare data
oplevert: API als die beschikbaar is, anders sitemap/RSS, en anders HTML-scrape.
Een bron hoeft niet standaard uit te blijven alleen omdat er geen API is.

De scraper-instellingen zijn bedoeld als operationele knoppen, niet als
principiele blokkade:

- `enabled` bepaalt of een bron actief meedraait.
- `queries` en `locations` laten een bron meerdere zoekcombinaties ophalen.
- `max_pages` begrenst pagina's per zoekcombinatie.
- `max_fetch_pages` begrenst het totale aantal zoekpagina's per bron.
- `max_resultaten` begrenst het aantal opgeslagen vacatures per bron.
- `fetch_details` en `max_detail_pages` verrijken sitemap-resultaten met
  vacaturedetaildata wanneer de site die publiek aanbiedt.
- `delay_seconds` voorkomt onnodige piekbelasting.
- `respect_robots_txt` is per bron configureerbaar.
- `stop_on_block` voorkomt dat een mislukte bron de hele pipeline verstoort.
- Caching (`data/cache/<bron>/`) voorkomt herhaald ophalen van dezelfde pagina's.

Gebruik alleen data die zonder account of persoonlijke sessie zichtbaar is. Voeg
geen API-sleutels, cookies, sessietokens of persoonlijke gegevens toe aan de
repository.

## Vacaturemodel

Elke provider levert dicts met dezelfde velden:
`titel`, `bedrijf`, `locatie`, `url`, `omschrijving`, `datum`, `bron`.
Zo blijft de rest van de pijplijn (scoren, renderen) bronnen-onafhankelijk.
