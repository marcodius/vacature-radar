# CLAUDE.md — Vacature Radar

Context voor Claude (of een andere AI) bij het werken aan dit project.

## Doel

Dagelijks Nederlandse vacatures ophalen, lokaal scoren op relevantie en
publiceren als een simpele statische GitHub Pages-site om te delen.

## Stack

- Python 3.12
- GitHub Actions (dagelijkse run)
- GitHub Pages (hosting)
- Geen database, geen backend, geen betaalde diensten in versie 1

## Architectuur

```
src/
  providers/
    nationale_vacaturebank.py   # primaire bron (mock-fallback, echte API via NVB_API_KEY)
    adzuna.py                   # extra bron, standaard uit (ADZUNA_APP_ID/KEY)
    arbeitnow.py                # extra bron, standaard uit (gratis, geen sleutel)
    manual_links.py             # handmatige links uit data/manual_links.json (bijv. LinkedIn)
  fetch_jobs.py                 # stap 1: ophalen -> data/jobs_raw.json
  score_jobs.py                 # stap 2: scoren  -> data/jobs_scored.json
  render_site.py                # stap 3: site    -> public/index.html
config/
  profile.example.json          # trefwoorden, locaties, uitsluiten, min_score
  sources.example.json          # bronnen aan/uit + opties
data/
  manual_links.example.json     # formaat voor handmatige links
```

### Provider-contract

Elke provider heeft `fetch(config) -> list[dict]`. Elke vacature is een dict met:
`titel`, `bedrijf`, `locatie`, `url`, `omschrijving`, `datum`, `bron`.
Zo blijft de rest van de pijplijn bronnen-onafhankelijk.

Bronnen zijn aan/uit te zetten via `config/sources.json` (`"aan": true/false`).

## Belangrijke regels

- Geen LinkedIn-scraping. LinkedIn alleen via handmatige links.
- Geen API-sleutels in code. Alleen via environment variables / GitHub Secrets.
- Geen persoonlijke gegevens publiceren (profiel en bronnen staan in `.gitignore`).
- Site in eenvoudig Nederlands, geen JavaScript-framework.
- Vacatures gesorteerd op hoogste score, met matchredenen.
- Houd het simpel en onderhoudbaar.

## Status

Versie 1: Nationale Vacaturebank draait op mock-data (geen gratis publieke API).
Adzuna en Arbeitnow zijn voorbereid maar standaard uit. Eerst uitbreiden nadat
de minimale versie werkt.

## Lokaal draaien

```bash
pip install -r requirements.txt
python src/fetch_jobs.py
python src/score_jobs.py
python src/render_site.py
```

## Zoekprofielen Kevin

Het systeem matcht vacatures tegen twee zoekprofielen voor Kevin
(`config/profile.kevin.json`, voorbeeld in `config/profile.kevin.example.json`).
Het uitgebreide scoremodel in `score_jobs.py` wordt automatisch gebruikt zodra
het profiel een `profiles`-lijst bevat.

### Algemene harde eisen

- Minimum salaris: € 3.300 bruto per maand op basis van 40 uur.
- Voorkeurssalaris: € 3.500 – € 4.500 bruto per maand.
- Hybride werken is verplicht. Vacatures die expliciet "volledig op kantoor"
  vermelden worden uitgesloten; ontbreekt de vermelding, dan volgt een
  waarschuwing (geen harde uitsluiting).
- Vacatures met een duidelijk vermeld salaris onder € 3.300 worden uitgesloten.

### Algemene dealbreakers

Uitsluiten of zeer lage score wanneer dit de hoofdtaak lijkt: hele dag telefonie,
callcenter, koude acquisitie, leads opvolgen als hoofdtaak, harde sales targets,
zeer formele/hiërarchische organisatie, functies die vrijwel uitsluitend
administratie zijn.

### Gewenste werkzaamheden (extra score)

CRM-/Salesforce-/HubSpot-beheer, procesoptimalisatie, automatiseringen,
projectondersteuning, operations, data-analyse en rapportages,
klantprocesverbeteringen, commerciële ondersteuning, administratie als onderdeel
van een bredere operationsfunctie.

### Gewenste werkomgeving (extra score)

Informele sfeer, geen pak-en-stropdas cultuur, moderne organisatie, tech/SaaS/
scale-up/dienstverlener, resultaatgericht en pragmatisch, ruimte voor eigen
initiatief en procesverbetering.

### Zoekprofiel 1 – Regio Midden/Oost

Locaties: Ede, Arnhem, Utrecht, Nijmegen, Amersfoort, en nabij Veenendaal en
Wageningen wanneer hybride werken mogelijk is.

### Zoekprofiel 2 – Amsterdam

Locaties: Amsterdam (Zuid, Amstel, Sloterdijk, Zuidoost). Goed bereikbaar met
trein/OV, bij voorkeur nabij een NS-station, geen slecht bereikbare
bedrijventerreinen. Hybride werken is een harde eis.

### Scoremodel (samengevat)

```
+35 titel prioriteit 1   +25 titel prioriteit 2   +20 werkzaamheden passen
+15 locatie past         +15 hybride genoemd       +10 SaaS/tech/scale-up
+10 CRM/Salesforce/HubSpot   +10 proces/automatisering/rapportage
+5  salaris boven voorkeursminimum
-100 geen hybride   -80 salaris onder 3300   -60 callcenter/telefonie
-60 koude acquisitie  -50 harde sales targets  -40 alleen administratie
-25 slecht bereikbaar zonder OV   -20 zeer formele cultuur
```

Labels: 80–100 Zeer interessant, 65–79 Interessant, 50–64 Mogelijk interessant,
0–49 Lage match. Harde dealbreakers of negatieve score → niet tonen, opslaan in
`data/rejected_jobs.json`.

Bijzondere regel: "Commercieel Medewerker Binnendienst" scoort alleen goed bij
support/operations-context (CRM, klantproces, orderverwerking, sales support);
bij koude acquisitie/targets/telefonie volgt een straf.

### Output op de website

Per vacature: matchscore, label, gematcht zoekprofiel, matchredenen,
waarschuwingen, dealbreaker-indicatie, salaris- en hybride-indicatie, locatie en
bron. Afgewezen vacatures staan niet op de publieke pagina maar in
`data/rejected_jobs.json` voor controle.
