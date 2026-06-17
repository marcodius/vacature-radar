"""Generieke ATS-provider voor losse werkgevers (grote bedrijven).

Veel werkgevers publiceren hun vacatures via een ATS met een publieke JSON-API.
Door per werkgever dat ene endpoint aan te roepen krijgen we nette, gestructureerde
data (titel, locatie, omschrijving, url) — inclusief locatie, zodat de strikte
locatiefilter de vacatures in een zoekgebied correct overhoudt.

Ondersteunde platforms (publieke endpoints, geen sleutel):
- greenhouse      : https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
- recruitee       : https://{board}.recruitee.com/api/offers/
- lever           : https://api.lever.co/v0/postings/{board}?mode=json
- smartrecruiters : https://api.smartrecruiters.com/v1/companies/{board}/postings

Config (in sources.json onder 'ats_bedrijven'):
  {
    "enabled": true, "type": "api", "priority": 20,
    "max_resultaten_per_werkgever": 100,
    "werkgevers": [
      {"naam": "Voorbeeld", "platform": "greenhouse", "board": "voorbeeld"}
    ]
  }
"board" is de identifier in de ATS-URL van de werkgever.
"""

import re

import requests

NAAM = "ATS"


def _strip_html(tekst):
    return re.sub(r"<[^>]+>", " ", tekst or "").replace("&nbsp;", " ").strip()


def _is_nl(locatie):
    """Alleen een NL-hint geven als de locatie echt NL is (anders telt een
    buitenlandse 'hybrid'-baan onterecht als remote-NL)."""
    laag = (locatie or "").lower()
    return "nl" if any(t in laag for t in ("nederland", "netherlands", "holland")) else ""


def _vacature(titel, bedrijf, locatie, url, omschrijving, datum):
    return {
        "titel": titel or "Onbekende functie",
        "bedrijf": bedrijf or "Onbekend bedrijf",
        "locatie": locatie or "Onbekend",
        "url": url or "",
        # Ruim afkappen: hybride- en salaris-vermeldingen staan vaak achteraan
        # (arbeidsvoorwaarden); te krap knippen kost matchsignaal.
        "omschrijving": _strip_html(omschrijving)[:12000],
        "datum": (datum or "")[:10],
        "bron": bedrijf or NAAM,
        "land": _is_nl(locatie),
    }


def _greenhouse(board, bedrijf, limiet):
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    data = requests.get(url, timeout=30).json()
    out = []
    for j in (data.get("jobs") or [])[:limiet]:
        loc = (j.get("location") or {}).get("name", "")
        out.append(_vacature(j.get("title"), bedrijf, loc, j.get("absolute_url"),
                             j.get("content", ""), j.get("updated_at", "")))
    return out


def _recruitee(board, bedrijf, limiet):
    url = f"https://{board}.recruitee.com/api/offers/"
    data = requests.get(url, timeout=30).json()
    out = []
    for o in (data.get("offers") or [])[:limiet]:
        loc = o.get("location") or o.get("city") or ""
        out.append(_vacature(o.get("title"), bedrijf, loc,
                             o.get("careers_url") or o.get("url"),
                             o.get("description", ""), o.get("published_at", "")))
    return out


def _lever(board, bedrijf, limiet):
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    data = requests.get(url, timeout=30).json()
    out = []
    for p in (data or [])[:limiet]:
        loc = (p.get("categories") or {}).get("location", "")
        out.append(_vacature(p.get("text"), bedrijf, loc, p.get("hostedUrl"),
                             p.get("descriptionPlain") or p.get("description", ""), ""))
    return out


def _smartrecruiters(board, bedrijf, limiet):
    url = f"https://api.smartrecruiters.com/v1/companies/{board}/postings?limit={min(limiet,100)}"
    data = requests.get(url, timeout=30).json()
    out = []
    for c in (data.get("content") or [])[:limiet]:
        loc = c.get("location") or {}
        plaats = loc.get("city") or loc.get("region") or ""
        url_v = f"https://jobs.smartrecruiters.com/{board}/{c.get('id')}" if c.get("id") else ""
        out.append(_vacature(c.get("name"), bedrijf, plaats, url_v, "",
                             c.get("releasedDate", "")))
    return out


PLATFORMS = {
    "greenhouse": _greenhouse,
    "recruitee": _recruitee,
    "lever": _lever,
    "smartrecruiters": _smartrecruiters,
}


def fetch(config):
    # 'werkgevers' = vaste set; 'watchlist' = kandidaten die we dagelijks
    # automatisch meenemen. Beide gaan door dezelfde relevantie-/locatiefilter,
    # dus een werkgever zonder passende rol levert vanzelf niets op; zodra er wel
    # een match is, verschijnt die automatisch.
    werkgevers = list(config.get("werkgevers", [])) + list(config.get("watchlist", []))
    limiet = int(config.get("max_resultaten_per_werkgever", 100))
    if not werkgevers:
        print("[ATS] Geen werkgevers geconfigureerd. Bron wordt overgeslagen.")
        return []

    gezien, resultaat = set(), []
    for wg in werkgevers:
        platform = (wg.get("platform") or "").lower()
        board = wg.get("board")
        bedrijf = wg.get("naam") or board
        fn = PLATFORMS.get(platform)
        if not fn or not board:
            print(f"[ATS] Werkgever '{bedrijf}': onbekend platform '{platform}' of geen 'board'. Overslaan.")
            continue
        try:
            rijen = fn(board, bedrijf, limiet)
        except Exception as fout:  # noqa: BLE001
            print(f"[ATS] '{bedrijf}' ({platform}) mislukt: {fout}. Overslaan.")
            continue
        nieuw = 0
        for v in rijen:
            sleutel = v.get("url") or (v["titel"], v["bedrijf"])
            if sleutel in gezien:
                continue
            gezien.add(sleutel)
            resultaat.append(v)
            nieuw += 1
        print(f"[ATS] {bedrijf} ({platform}): {nieuw} vacatures.")
    print(f"[ATS] Totaal {len(resultaat)} vacatures uit {len(werkgevers)} werkgever(s).")
    return resultaat
