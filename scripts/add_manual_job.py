#!/usr/bin/env python3
"""Voeg een vacature handmatig toe aan data/manual_links.json.

Gebruik:
    python3 scripts/add_manual_job.py <url> [--titel ...] [--bedrijf ...] \
        [--locatie ...] [--omschrijving ...] [--bron linkedin_manual|indeed_manual|manual]

Gedrag:
- Voor publieke vacaturepagina's haalt het script de pagina eenmalig op en vult
  titel/bedrijf/locatie voor uit Open Graph of JSON-LD (JobPosting).
- Meegegeven opties overschrijven altijd.
- De vacature wordt toegevoegd aan data/manual_links.json (ontdubbeld op url),
  in hetzelfde formaat dat de manual-provider verwacht.
"""

import argparse
import json
import os
import sys
import urllib.robotparser
from urllib.parse import urlparse

import requests

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PAD = os.path.join(PROJECT_DIR, "data", "manual_links.json")
USER_AGENT = "vacature-radar/1.0 (+https://github.com/marcodius/vacature-radar; persoonlijk project)"

def _host(url):
    return (urlparse(url).hostname or "").lower()


def _bron_voor(url, expliciet):
    if expliciet:
        return expliciet
    h = _host(url)
    if "linkedin.com" in h:
        return "linkedin_manual"
    if "indeed." in h:
        return "indeed_manual"
    return "manual"


def _robots_toestaan(url):
    deel = urlparse(url)
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(f"{deel.scheme}://{deel.netloc}/robots.txt")
    try:
        rp.read()
    except Exception:  # noqa: BLE001
        return False
    return rp.can_fetch(USER_AGENT, url)


def _extraheer_velden(html):
    """Haal titel/bedrijf/locatie uit Open Graph of JSON-LD JobPosting."""
    velden = {}
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return velden
    soup = BeautifulSoup(html, "html.parser")

    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        velden["titel"] = og["content"].strip()

    import json as _json
    for s in soup.find_all("script", type="application/ld+json"):
        try:
            data = _json.loads(s.string or "")
        except Exception:  # noqa: BLE001
            continue
        for obj in (data if isinstance(data, list) else [data]):
            if not isinstance(obj, dict):
                continue
            if "JobPosting" in str(obj.get("@type", "")):
                velden.setdefault("titel", (obj.get("title") or "").strip())
                org = obj.get("hiringOrganization") or {}
                if isinstance(org, dict) and org.get("name"):
                    velden["bedrijf"] = org["name"].strip()
                loc = obj.get("jobLocation") or {}
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                adres = (loc or {}).get("address") or {}
                if isinstance(adres, dict) and adres.get("addressLocality"):
                    velden["locatie"] = adres["addressLocality"].strip()
    return velden


def main():
    p = argparse.ArgumentParser(description="Voeg een vacature toe aan data/manual_links.json")
    p.add_argument("url")
    p.add_argument("--titel")
    p.add_argument("--bedrijf")
    p.add_argument("--locatie")
    p.add_argument("--omschrijving")
    p.add_argument("--bron", help="linkedin_manual | indeed_manual | manual")
    args = p.parse_args()

    bron = _bron_voor(args.url, args.bron)
    host = _host(args.url)

    velden = {}
    if _robots_toestaan(args.url):
        try:
            resp = requests.get(args.url, headers={"User-Agent": USER_AGENT}, timeout=30)
            if resp.status_code < 400:
                velden = _extraheer_velden(resp.text)
                print(f"[add] Pagina opgehaald; voorgevuld: {list(velden)}")
            else:
                print(f"[add] HTTP {resp.status_code}; alleen meegegeven velden gebruiken.")
        except Exception as fout:  # noqa: BLE001
            print(f"[add] Ophalen mislukt: {fout}; alleen meegegeven velden gebruiken.")
    else:
        print("[add] robots.txt staat ophalen niet toe; alleen meegegeven velden gebruiken.")

    # Meegegeven opties overschrijven voorgevulde velden.
    entry = {
        "source": bron,
        "title": args.titel or velden.get("titel") or "Onbekende functie",
        "company": args.bedrijf or velden.get("bedrijf") or "Onbekend bedrijf",
        "location": args.locatie or velden.get("locatie") or "Onbekend",
        "url": args.url,
    }
    if args.omschrijving:
        entry["notes"] = args.omschrijving

    # Inladen, ontdubbelen op url, opslaan.
    items = []
    if os.path.exists(DATA_PAD):
        try:
            with open(DATA_PAD, "r", encoding="utf-8") as f:
                items = json.load(f)
            if not isinstance(items, list):
                items = []
        except Exception:  # noqa: BLE001
            items = []

    if any(i.get("url") == entry["url"] for i in items):
        print(f"[add] Bestaat al, niet toegevoegd: {entry['url']}")
        return

    items.append(entry)
    os.makedirs(os.path.dirname(DATA_PAD), exist_ok=True)
    with open(DATA_PAD, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    print(f"[add] Toegevoegd ({bron}): {entry['title']} — {entry['company']} ({entry['location']})")
    print(f"[add] Totaal {len(items)} handmatige vacatures in {DATA_PAD}")


if __name__ == "__main__":
    main()
