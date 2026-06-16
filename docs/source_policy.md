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

Scrape-bronnen staan standaard uit (`"enabled": false`). Zet ze één voor één
aan en controleer of ze stabiel en netjes werken. De HTML-selectors zijn
best-effort en kunnen aangepast moeten worden als een site wijzigt.

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
