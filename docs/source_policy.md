# Bronbeleid — Vacature Radar

Doel: meer Nederlandse vacaturedekking zonder risicovolle scraping of
platformmisbruik. Elke bron komt binnen via de veiligste route per platform.

## Bronnen en methode

| Bron | Meenemen? | Methode |
| --- | --- | --- |
| Nationale Vacaturebank | Ja | API (`NVB_API_KEY`) |
| Vacatures Overheid (CSO) | Ja | API (`CSO_API_KEY`) |
| Jooble NL | Ja | API (`JOOBLE_API_KEY`) |
| Adzuna NL | Ja | API (`ADZUNA_APP_ID` + `ADZUNA_APP_KEY`) |
| Werk.nl | Ja | Polite scrape |
| Jobbird (`jobbird.com/nl/vacature/`) | Ja | Polite scrape |
| Randstad | Ja | Polite scrape |
| YoungCapital | Ja | Polite scrape |
| LinkedIn | Ja, niet scrapen | Manual import |
| Indeed | Ja, niet scrapen | Manual import |
| Monsterboard | Nee | Verwijderd (Monster Nederland failliet) |

API-sleutels staan nooit in de code; alleen in environment variables /
GitHub Secrets.

## Regels voor polite scraping (Werk.nl, Jobbird, Randstad, YoungCapital)

Deze regels worden afgedwongen in `src/providers/scrape/_polite.py`:

- Alleen publieke vacaturezoekpagina's en vacaturedetailpagina's.
- Respecteer `robots.txt`. Niet leesbaar of niet toegestaan → niet ophalen.
- Maximaal 1 dagelijkse run.
- Maximaal 2 zoekresultaatpagina's per bron.
- Minimaal 10 seconden delay tussen requests.
- Caching van opgehaalde pagina's (`data/cache/<bron>/`, ~20 uur geldig).
- Stop bij 403, 429, CAPTCHA, login-wall of andere blokkade.
- Geen proxies. Geen IP-rotatie. Geen CAPTCHA-bypass.
- Geen browser-fingerprinting of stealth. Geen browser-automation om detectie
  te ontwijken.
- Geen scraping achter login.
- Duidelijke user-agent met projectnaam.

De HTML-selectors zijn best-effort en kunnen aangepast moeten worden als een
site wijzigt.

### Robots- en haalbaarheidscheck (juni 2026)

| Bron | robots.txt | Statische HTML bruikbaar? | Status |
| --- | --- | --- | --- |
| Randstad | `/vacatures/` toegestaan | Ja — echte vacaturelinks aanwezig | **Aan** |
| Werk.nl | vacatures toegestaan | Nee — volledig JavaScript-gerenderd | Uit |
| Jobbird | zoekpagina's verboden (`Disallow: /nl/vacature?*`) | n.v.t. | Uit |
| YoungCapital | relevante categorie-/zoekpagina's verboden | n.v.t. | Uit |

Alleen Randstad is robots-toegestaan én bruikbaar met een statische scraper en
staat daarom aan. De andere drie blijven uit; de reden staat per bron in
`config/sources.example.json` (`_reden_uit`). Werk.nl en Randstad kunnen later
alsnog via een (zwaardere) gerenderde aanpak, maar dat valt buiten versie 1.

## Sitemaps als gratis route (geen betaalde scrape-diensten)

Sommige sites verbieden hun zoekpagina's in robots.txt (Jobbird, YoungCapital)
of zijn volledig JavaScript-gerenderd (Werk.nl). Daarvoor gebruiken we de
officiele **sitemap** die de site zelf publiceert en in robots.txt aankondigt —
de door de site bedoelde crawl-route. We lezen er vacature-URL's uit en leiden
de titel af uit de URL-slug (`src/providers/scrape/sitemap_source.py`, met de
gedeelde `_polite`-regels: robots, delay, caching, stop bij blokkade).

Dit is bewust een gratis alternatief voor betaalde scrape-diensten zoals Apify.
Apify-actors voor o.a. Werk.nl en Nationale Vacaturebank doen hetzelfde, maar
vereisen een account, API-token en credits (kosten). Dat botst met het
uitgangspunt "geen betaalde diensten in versie 1" en wordt daarom niet gebruikt.

Sitemap-bronnen leveren titel + locatie + link, maar geen salaris/bedrijf/
volledige tekst (dat zou per vacature een detailpagina-fetch vereisen).

**Overheidsvacatures gratis via WerkenvoorNederland.** De open dataset
"Vacatures Overheid" op data.overheid.nl verwijst alleen naar de CSO-API
(`docs.api.cso20.net`), die een sleutel vereist. Hetzelfde aanbod
(WerkenvoorNederland / WerkenbijdeOverheid) is gratis te halen via de sitemap:
`werkenvoornederland.nl/robots.txt` staat crawlen toe (alleen `/login` verboden)
en publiceert expliciet `sitemap-vacatures.xml`. Daarom is `werkenvoornederland_sitemap`
aan; de sleutel-gebaseerde `vacatures_overheid` (CSO-API) is optioneel voor
rijkere data.

`werk_nl_sitemap` en `nationale_vacaturebank_sitemap` staan klaar maar uit:
verifieer eerst de juiste `sitemap_url` en `detail_bevat` op een machine die de
site kan bereiken, en respecteer de actuele robots.txt.

## LinkedIn en Indeed — alleen handmatig

LinkedIn en Indeed worden **niet** automatisch opgehaald of gescrapet. Er gaan
**geen** requests naar `linkedin.com` of `indeed.com`. Dit is bewust: het zijn
precies de platforms waar geautomatiseerde dataverzameling snel overgaat in
account- of platformmisbruik, en waar actief op scraping wordt gedetecteerd.

Vacatures van deze platforms voeg je handmatig toe in `data/manual_links.json`
met een `source` van `linkedin_manual` of `indeed_manual`. De manual-provider
normaliseert ze naar hetzelfde vacaturemodel als de andere bronnen.

Voorbeeld:

```json
[
  {
    "source": "linkedin_manual",
    "title": "Business Development Manager SaaS",
    "company": "Voorbeeld BV",
    "location": "Amsterdam / Hybride",
    "url": "https://www.linkedin.com/jobs/view/...",
    "notes": "Handmatig toegevoegd"
  },
  {
    "source": "indeed_manual",
    "title": "Accountmanager Tech",
    "company": "Voorbeeld BV",
    "location": "Utrecht",
    "url": "https://nl.indeed.com/viewjob?jk=...",
    "notes": "Handmatig toegevoegd"
  }
]
```

## Vacaturemodel

Elke provider levert dicts met dezelfde velden:
`titel`, `bedrijf`, `locatie`, `url`, `omschrijving`, `datum`, `bron`.
Zo blijft de rest van de pijplijn (scoren, renderen) bronnen-onafhankelijk.
