# Projectinstructie — Vacature Radar

Herschreven instructie die de huidige staat van het project weergeeft. Plak dit
in de projectinstellingen (en zie ook `CLAUDE.md` en `docs/source_policy.md`).

## Doel

Haal dagelijks Nederlandse vacatures op, scoor ze lokaal op relevantie tegen
twee zoekprofielen voor Kevin, en publiceer het resultaat als een simpele
statische GitHub Pages-site om te delen.

## Stack en uitgangspunten

- Python 3.12, GitHub Actions (dagelijkse run), GitHub Pages (hosting).
- Geen database, geen backend, geen JavaScript-framework.
- **Geen betaalde diensten** — ook geen betaalde scrape-platforms zoals Apify.
- Houd het simpel en onderhoudbaar.

## Architectuur

```
src/providers/
  api/        nationale_vacaturebank, vacatures_overheid, jooble, adzuna
  scrape/     randstad, jobbird, werk_nl, youngcapital, sitemap_source (+ _polite)
  manual/     manual_links (LinkedIn + Indeed, handmatig)
  provider_registry.py        koppelt bronsleutel -> provider
src/fetch_jobs.py             stap 1: ophalen  -> data/jobs_raw.json
src/score_jobs.py             stap 2: scoren   -> data/jobs_scored.json + rejected_jobs.json
src/render_site.py            stap 3: site     -> public/index.html
config/  sources.example.json, profile.kevin.example.json
docs/    source_policy.md
```

Elke provider biedt `fetch(config) -> list[dict]` met velden `titel`, `bedrijf`,
`locatie`, `url`, `omschrijving`, `datum`, `bron`. Bronnen staan in
`config/sources.json` onder `"sources"` met `enabled`, `type`
(`api`/`polite_scrape`/`manual`) en `priority`. Een bron toevoegen = één regel in
`provider_registry.py` plus een configblok.

## Bronbeleid (zie docs/source_policy.md)

API-bronnen (gratis, sleutel via environment variables / GitHub Secrets; zonder
sleutel netjes overgeslagen):
- Nationale Vacaturebank (`NVB_API_KEY`), Vacatures Overheid (`CSO_API_KEY`),
  Jooble NL (`JOOBLE_API_KEY`), Adzuna NL (`ADZUNA_APP_ID` + `ADZUNA_APP_KEY`).

Gratis scrape-/sitemap-bronnen (volgen polite-regels):
- Randstad (statische scrape, robots staat toe).
- Jobbird, Werk.nl, Nationale Vacaturebank via hun officiele **sitemap**
  (`sitemap_source`) — het gratis alternatief voor betaalde actors.
- YoungCapital: uit (robots verbiedt de relevante pagina's).

Manual-only: LinkedIn en Indeed. Nooit scrapen, geen requests naar die platforms;
alleen via `data/manual_links.json` (`source`: `linkedin_manual`/`indeed_manual`).

Monsterboard is verwijderd (Monster Nederland failliet).

### Polite-scrape regels (afgedwongen in scrape/_polite.py)

- Alleen publieke zoek-/detailpagina's of de officiele sitemap.
- Respecteer robots.txt; stop bij 403/429/CAPTCHA/login-wall.
- Max 1 dagelijkse run, max 2 pagina's per bron, min. 10s delay, caching.
- Geen proxies, IP-rotatie, CAPTCHA-bypass, stealth/fingerprinting,
  browser-automation om detectie te ontwijken, of scraping achter login.
- Duidelijke user-agent met projectnaam.

## Beveiliging en privacy

- API-sleutels staan nooit in code; alleen environment variables / GitHub Secrets.
- Geen persoonlijke gegevens publiceren. `config/profile*.json`,
  `config/sources.json` en `data/manual_links.json` staan in `.gitignore`.

## Scoremodel (Kevin — twee zoekprofielen)

Profiel in `config/profile.kevin.json` (voorbeeld: `.kevin.example.json`). Het
uitgebreide model in `score_jobs.py` wordt gebruikt zodra het profiel een
`profiles`-lijst bevat. Volgorde: 1) harde filters (hybride, salaris,
dealbreakers, locatie), 2) titelmatch (prio 1/2), 3) inhoud (CRM/operations/
proces), 4) context (locatie, OV, SaaS/cultuur), 5) sorteren en publiceren.

- Harde eisen: salaris ≥ €3.300 (40u); hybride verplicht (expliciet "volledig op
  kantoor" = uitsluiten, niet vermeld = waarschuwing); dealbreakers
  (callcenter/telefonie, koude acquisitie, harde targets, alleen administratie).
- Locatie: alleen Nederland; Amerikaanse locaties (TX/Texas/Beaumont/Groves,
  incl. "Nederland, TX") afwijzen; buiten de twee zoekgebieden = dealbreaker
  tenzij expliciet remote NL/Europe.
- Twee zoekgebieden: regio Ede/Arnhem/Utrecht/Nijmegen/Amersfoort en Amsterdam.
- Labels: 80–100 Zeer interessant, 65–79 Interessant, 50–64 Mogelijk, 0–49 Laag.
  Dealbreakers/negatief → `data/rejected_jobs.json` (niet publiek getoond).

## Website

Statisch, eenvoudig Nederlands, geen framework. Bovenaan een samenvatting
(opgehaald / getoonde topmatches / afgewezen dealbreakers / verborgen lage
matches). Alleen score ≥ 50 bij "Topmatches"; lagere matches in een ingeklapte
sectie "Lage matches / ter controle". Per vacature: score, label, zoekprofiel,
matchredenen, waarschuwingen, dealbreaker-indicatie, salaris- en hybride-
indicatie, locatie en bron.

## Werkwijze bij wijzigingen

- Onderzoek eerst de bron (robots.txt, API-docs) voordat je een bron aanzet.
- Begin klein, zet nieuwe scrape-/sitemap-bronnen standaard uit en verifieer ze
  één voor één live.
- Maak alleen noodzakelijke wijzigingen; voeg geen risicovolle scraping of
  betaalde diensten toe.

## Lokaal draaien

```bash
pip install -r requirements.txt
cp config/sources.example.json config/sources.json
cp config/profile.kevin.example.json config/profile.kevin.json
python src/fetch_jobs.py && python src/score_jobs.py && python src/render_site.py
```
