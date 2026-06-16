# Vacature Radar

Haalt dagelijks Nederlandse vacatures op, scoort ze lokaal op relevantie en
publiceert het resultaat als een simpele statische website op GitHub Pages.
Bedoeld om makkelijk te delen (bijvoorbeeld met familie).

Versie 1 is bewust simpel: geen database, geen backend, geen betaalde diensten.

## Hoe het werkt

De pijplijn bestaat uit drie stappen die je los kunt draaien:

1. `python3 src/fetch_jobs.py` — haalt vacatures op uit de ingeschakelde bronnen
   en slaat ze op in `data/jobs_raw.json`.
2. `python3 src/score_jobs.py` — scoort elke vacature op basis van je profiel en
   slaat het gesorteerde resultaat op in `data/jobs_scored.json`.
3. `python3 src/render_site.py` — bouwt de website in `public/index.html`.

## Lokaal draaien

```bash
/Library/Frameworks/Python.framework/Versions/3.13/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# Kopieer de voorbeeld-config naar echte config (eenmalig)
cp config/profile.example.json config/profile.json
cp config/sources.example.json config/sources.json
cp data/manual_links.example.json data/manual_links.json   # optioneel

python src/fetch_jobs.py
python src/score_jobs.py
python src/render_site.py
```

Open daarna `public/index.html` in je browser.

> Tip: de scripts werken ook zonder eigen config — dan gebruiken ze automatisch
> de `.example`-bestanden.

## Projectstructuur

```
src/providers/
  api/        nationale_vacaturebank, vacatures_overheid, jooble, adzuna
  scrape/     werk_nl, jobbird, randstad, youngcapital, linkedin, indeed (+ _polite helper)
  manual/     manual_links (fallback voor handmatige vacaturelinks)
  provider_registry.py   koppelt bronsleutel -> provider
src/fetch_jobs.py / score_jobs.py / render_site.py
config/   sources.example.json, profile(.kevin).example.json
docs/     source_policy.md
```

Elke provider biedt `fetch(config) -> list[dict]` met velden `titel`, `bedrijf`,
`locatie`, `url`, `omschrijving`, `datum`, `bron`. Een bron toevoegen = één regel
in `provider_registry.py` plus een blok in `config/sources.json`.

## Bronnen

Bronnen staan in `config/sources.json` onder `"sources"`. Per bron: `enabled`
(aan/uit), `type` (`api` / `polite_scrape` / `manual`) en `priority`
(ophaalvolgorde). Het volledige bronbeleid staat in
[`docs/source_policy.md`](docs/source_policy.md).

Scrape-bronnen ondersteunen bredere dekking via:

- `queries`: meerdere zoektermen per bron.
- `locations`: meerdere locaties per bron.
- `max_pages`: aantal pagina's per query/locatie-combinatie.
- `max_fetch_pages`: harde bovengrens op het totaal aantal zoekpagina's per bron.
- `max_resultaten`: bovengrens op opgeslagen vacatures per bron.
- `fetch_details` + `max_detail_pages`: verrijk sitemap-resultaten met velden uit
  vacaturedetailpagina's.

**API-bronnen** (sleutels via environment variables / GitHub Secrets; zonder
sleutel wordt de bron netjes overgeslagen):

- **Nationale Vacaturebank** — `NVB_API_KEY`.
- **Vacatures Overheid (CSO)** — `CSO_API_KEY`. Docs: https://docs.api.cso20.net/
- **Jooble NL** — `JOOBLE_API_KEY`.
- **Adzuna NL** — `ADZUNA_APP_ID` + `ADZUNA_APP_KEY` (https://developer.adzuna.com/).

**Scrape-bronnen** (configureerbaar per bron; zie `docs/source_policy.md`):

- **Werk.nl**, **Jobbird** (via `jobbird.com/nl/vacature/`), **Randstad**,
  **YoungCapital**, **LinkedIn**, **Indeed**, **Intermediair**, **Talent.com**,
  **Jobrapido**, **SimplyHired**, **Joblift** en andere sites met publiek
  toegankelijke vacaturepagina's.
- Sitemaps en RSS-feeds zijn ook geldige scrape-routes wanneer die meer stabiele
  data leveren dan zoekpagina's.

**Handmatige bronnen** (fallback wanneer automatisch ophalen nog niet is
ingericht):

- Voeg vacatures toe in `data/manual_links.json`, bijvoorbeeld met `source`
  `linkedin_manual` of `indeed_manual`.

> Monsterboard is verwijderd: Monster Nederland is failliet en geen bruikbare
> bron meer.

## API-sleutels

Sleutels staan **nooit** in de code. Lokaal geef je ze mee als environment
variables, bijvoorbeeld:

```bash
export NVB_API_KEY="..."
export ADZUNA_APP_ID="..."
export ADZUNA_APP_KEY="..."
export JOOBLE_API_KEY="..."
```

In GitHub Actions zet je dezelfde namen als **GitHub Secrets**
(Settings → Secrets and variables → Actions).

## Zoekprofielen (Kevin)

Naast het eenvoudige profiel is er een uitgebreid profiel met twee zoekprofielen
(`config/profile.kevin.example.json`): regio Midden/Oost en Amsterdam. Kopieer het
naar `config/profile.kevin.json` om het te gebruiken; `score_jobs.py` schakelt
automatisch over op het uitgebreide model zodra het profiel een `profiles`-lijst
bevat. Dit model past harde filters toe (hybride, salaris, dealbreakers), matcht
op functietitel en inhoud, kent labels en waarschuwingen toe, en zet afgewezen
vacatures apart in `data/rejected_jobs.json`. Zie CLAUDE.md voor het volledige
scoremodel.

## Je (eenvoudige) profiel aanpassen

In `config/profile.json` zet je je trefwoorden, gewenste locaties en woorden om
uit te sluiten. De score werkt zo:

- Trefwoord in de titel: **+2**
- Trefwoord in de tekst: **+1**
- Gewenste locatie gevonden: **+2**
- Uitsluitwoord aanwezig: **−5**

Vacatures onder `min_score` worden niet getoond. De lijst staat gesorteerd op
hoogste score, met per vacature de matchredenen.

## Automatisch via GitHub Actions

`.github/workflows/daily.yml` draait de pijplijn elke dag en publiceert naar
GitHub Pages. Zet in de repo-instellingen GitHub Pages op "GitHub Actions".

## Privacy

Er worden geen persoonlijke gegevens gepubliceerd. `config/profile.json`,
`config/sources.json` en `data/manual_links.json` staan in `.gitignore`.
