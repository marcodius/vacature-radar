"""Gedeelde hulpmiddelen voor nette ('polite') scrapers.

Afspraken die hier worden afgedwongen (zie ook docs/source_policy.md):
- Respecteer robots.txt.
- Maximaal N zoekresultaatpagina's per bron (config 'max_pages', standaard 2).
- Minimaal 10 seconden delay tussen requests (config 'delay_seconds').
- Caching van opgehaalde pagina's (data/cache/<bron>/), standaard ~20 uur geldig.
- Stop bij 403, 429, CAPTCHA, login-wall of andere blokkade.
- Geen proxies, geen IP-rotatie, geen CAPTCHA-bypass, geen stealth/fingerprinting,
  geen browser-automation, geen scraping achter login.
- Duidelijke user-agent met projectnaam.

De scrapers gebruiken alleen publieke zoek- en detailpagina's.
"""

import hashlib
import os
import time
import urllib.robotparser
from urllib.parse import urlparse

import requests

PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
CACHE_DIR = os.path.join(PROJECT_DIR, "data", "cache")

USER_AGENT = (
    "vacature-radar/1.0 (+https://github.com/marcodius/vacature-radar; "
    "persoonlijk vacature-zoekproject)"
)
CACHE_GELDIG_SECONDEN = 20 * 3600


class Geblokkeerd(Exception):
    """Opgeworpen bij 403/429/CAPTCHA/login-wall, zodat we netjes stoppen."""


def _cache_pad(bron, url):
    sleutel = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return os.path.join(CACHE_DIR, bron, sleutel + ".html")


def _lees_cache(pad):
    if os.path.exists(pad) and (time.time() - os.path.getmtime(pad)) < CACHE_GELDIG_SECONDEN:
        with open(pad, "r", encoding="utf-8") as f:
            return f.read()
    return None


def _schrijf_cache(pad, inhoud):
    os.makedirs(os.path.dirname(pad), exist_ok=True)
    with open(pad, "w", encoding="utf-8") as f:
        f.write(inhoud)


def _blokkade_in_html(html):
    laag = html.lower()
    signalen = ["captcha", "recaptcha", "cf-challenge", "are you a human",
                "log in to continue", "inloggen om verder", "access denied"]
    return any(s in laag for s in signalen)


class PoliteSession:
    """Nette HTTP-sessie met robots-check, delay, caching en stop-bij-blokkade."""

    def __init__(self, bron, config):
        self.bron = bron
        self.delay = max(10, int(config.get("delay_seconds", 10)))
        self.respect_robots = config.get("respect_robots_txt", True)
        self.stop_on_block = config.get("stop_on_block", True)
        self._laatste_request = 0.0
        self._robots_cache = {}

    def _robots_toestaan(self, url):
        if not self.respect_robots:
            return True
        deel = urlparse(url)
        basis = f"{deel.scheme}://{deel.netloc}"
        rp = self._robots_cache.get(basis)
        if rp is None:
            rp = urllib.robotparser.RobotFileParser()
            rp.set_url(basis + "/robots.txt")
            try:
                rp.read()
            except Exception:  # noqa: BLE001 - geen robots leesbaar -> voorzichtig: niet toestaan
                print(f"[{self.bron}] robots.txt niet leesbaar voor {basis}. Overslaan.")
                self._robots_cache[basis] = False
                return False
            self._robots_cache[basis] = rp
        if rp is False:
            return False
        return rp.can_fetch(USER_AGENT, url)

    def get(self, url):
        """Haal een pagina op. Geeft HTML of None. Werpt Geblokkeerd bij blokkade."""
        cache_pad = _cache_pad(self.bron, url)
        gecachet = _lees_cache(cache_pad)
        if gecachet is not None:
            return gecachet

        if not self._robots_toestaan(url):
            print(f"[{self.bron}] robots.txt staat {url} niet toe. Overslaan.")
            return None

        # Delay tussen echte requests (cache telt niet mee).
        wacht = self.delay - (time.time() - self._laatste_request)
        if wacht > 0:
            time.sleep(wacht)

        try:
            resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        except Exception as fout:  # noqa: BLE001
            print(f"[{self.bron}] Request mislukt: {fout}. Stoppen met deze bron.")
            raise Geblokkeerd(str(fout))
        finally:
            self._laatste_request = time.time()

        if resp.status_code in (403, 429):
            raise Geblokkeerd(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            print(f"[{self.bron}] HTTP {resp.status_code} voor {url}. Overslaan.")
            return None
        if _blokkade_in_html(resp.text):
            raise Geblokkeerd("CAPTCHA/login-wall gedetecteerd")

        _schrijf_cache(cache_pad, resp.text)
        return resp.text


def extraheer_vacatures(html, detail_bevat, basis_url, bron):
    """Best-effort extractie van vacatures uit een zoekresultaatpagina.

    Zoekt links naar detailpagina's (href bevat 'detail_bevat'). Niet elke site
    heeft titel/bedrijf/locatie in de lijst; ontbrekende velden worden 'Onbekend'.
    De selectors zijn bewust generiek; pas ze aan als een site wijzigt.
    """
    from urllib.parse import urljoin

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[{bron}] beautifulsoup4 niet geinstalleerd. Bron wordt overgeslagen.")
        return []

    soup = BeautifulSoup(html, "html.parser")
    gezien, resultaat = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if detail_bevat not in href:
            continue
        url = urljoin(basis_url, href)
        if url in gezien:
            continue
        titel = " ".join(a.get_text(" ", strip=True).split())
        if not titel or len(titel) < 3:
            continue
        gezien.add(url)
        resultaat.append({
            "titel": titel,
            "bedrijf": "Onbekend bedrijf",
            "locatie": "Nederland",
            "url": url,
            "omschrijving": "",
            "datum": "",
            "bron": bron,
        })
    return resultaat


def haal_pagina_html(bron, page_urls, config):
    """Haal tot max_pages pagina's op; stop netjes bij een blokkade."""
    max_pages = min(int(config.get("max_pages", 2)), 2)
    sessie = PoliteSession(bron, config)
    htmls = []
    for url in page_urls[:max_pages]:
        try:
            html = sessie.get(url)
        except Geblokkeerd as blok:
            print(f"[{bron}] Geblokkeerd ({blok}). Stop met deze bron.")
            break
        if html:
            htmls.append(html)
    return htmls
