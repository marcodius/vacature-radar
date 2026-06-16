# Vacature Radar

Haalt dagelijks Nederlandse vacatures op, scoort ze lokaal op relevantie en
publiceert het resultaat als een simpele statische website op GitHub Pages.
Bedoeld om makkelijk te delen (bijvoorbeeld met familie).

Versie 1 is bewust simpel: geen database, geen backend, geen betaalde diensten.

## Hoe het werkt

De pijplijn bestaat uit drie stappen die je los kunt draaien:

1. `python src/fetch_jobs.py` — haalt vacatures op uit de ingeschakelde bronnen
   en slaat ze op in `data/jobs_raw.json`.
2. `python src/score_jobs.py` — scoort elke vacature op basis van je profiel en
   slaat het gesorteerde resultaat op in `data/jobs_scored.json`.
3. `python src/render_site.py` — bouwt de website in `public/index.html`.

## Lokaal draaien

```bash
pip install -r requirements.txt

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

## Bronnen

Bronnen staan in `config/sources.json` en kun je per stuk aan- of uitzetten met
`"aan": true/false`.

- **Nationale Vacaturebank** (primaire bron). De Nationale Vacaturebank heeft
  geen gratis openbare API; officiele toegang loopt via een API-sleutel die je
  met een account aanvraagt. Daarom staat de bron standaard op `"gebruik_mock": true`
  en levert hij voorbeeldvacatures, zodat de pijplijn meteen werkt. Heb je echte
  toegang? Zet `gebruik_mock` op `false` en lever de sleutel via de environment
  variable `NVB_API_KEY`.
- **Adzuna Nederland** (fase 2, uit). Brede NL-dekking. Vereist `ADZUNA_APP_ID`
  en `ADZUNA_APP_KEY` (gratis account via https://developer.adzuna.com/). Zet
  `"aan": true` zodra je de sleutels hebt; zonder sleutels wordt de bron
  automatisch overgeslagen. `trefwoorden` mag een lijst zijn.
- **Jooble** (fase 2, uit). Gratis REST-API; vraag een sleutel aan en zet die in
  `JOOBLE_API_KEY`. Zet `"aan": true` zodra je de sleutel hebt.
- **Overheid (CSO Vacature API)** (fase 2, uit). Overheidsvacatures van
  WerkenvoorNederland e.a. Gratis open data (CC-0), maar vereist een API-sleutel
  (`CSO_API_KEY`) uit een gratis account. Documentatie: https://docs.api.cso20.net/
- **RSS-feeds** (aan). Leest officiele RSS/Atom-feeds die boards zelf publiceren
  — geen scraping. Voorgeconfigureerd met 5 Resumo-feeds (ICT/management) waarvan
  je per functie nog de echte URL invult in `config/sources.json`; placeholder-URL's
  worden automatisch overgeslagen. Werkt voor elk board met een eigen feed.
- **Jobicy** (aan). Gratis remote-jobs API zonder sleutel. Internationaal/remote;
  we filteren lokaal op CRM/operations/SaaS-trefwoorden (`post_filter_keywords`).
  Bronvermelding "Jobicy" is verplicht en zit in de output.
- **Arbeitnow** (fase 2, uit). Gratis API zonder sleutel.
- **Handmatige links** (bijv. LinkedIn). Voeg zelf vacatures toe in
  `data/manual_links.json`. LinkedIn wordt **niet** gescrapet.

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
