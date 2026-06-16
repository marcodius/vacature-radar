"""Gedeelde hulpmiddelen voor nette ('polite') scrapers.

Afspraken die hier worden afgedwongen of per bron configureerbaar zijn
(zie ook docs/source_policy.md):
- Scraping is toegestaan voor publiek toegankelijke vacaturepagina's.
- Maximaal N zoekresultaatpagina's per bron (config 'max_pages', standaard 2).
- Minimaal 10 seconden delay tussen requests (config 'delay_seconds').
- Caching van opgehaalde pagina's (data/cache/<bron>/), standaard ~20 uur geldig.
- Robots-check is configureerbaar met 'respect_robots_txt'.
- Stopgedrag bij 403, 429, CAPTCHA, login-wall of andere blokkade is
  configureerbaar met 'stop_on_block'.
- Duidelijke user-agent met projectnaam.

De scrapers gebruiken publieke zoek-, sitemap- en detailpagina's.
"""

import hashlib
import json
import os
import time
import urllib.robotparser
from urllib.parse import urlencode, urljoin, urlparse

import requests

PROJECT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
CACHE_DIR = os.path.join(PROJECT_DIR, "data", "cache")

USER_AGENT = (
    "vacature-radar/1.0 (+https://github.com/marcodius/vacature-radar; "
    "persoonlijk vacature-zoekproject)"
)
DEFAULT_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
}
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
        self.delay = max(0, float(config.get("delay_seconds", 10)))
        self.respect_robots = config.get("respect_robots_txt", False)
        self.stop_on_block = config.get("stop_on_block", True)
        self.detect_block_html = config.get("detect_block_html", True)
        self.headers = {**DEFAULT_HEADERS, **config.get("headers", {})}
        if config.get("user_agent"):
            self.headers["User-Agent"] = config["user_agent"]
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
        return rp.can_fetch(self.headers.get("User-Agent", USER_AGENT), url)

    def get_bytes(self, url):
        """Als get(), maar geeft ruwe bytes terug en pakt gzip uit (voor sitemaps).

        Veel sitemaps worden gzip-gecomprimeerd aangeboden (.xml die in feite
        gzip is). Deze methode detecteert de gzip-magic en pakt uit.
        """
        import gzip as _gzip

        cache_pad = _cache_pad(self.bron, url) + ".bin"
        if os.path.exists(cache_pad) and (time.time() - os.path.getmtime(cache_pad)) < CACHE_GELDIG_SECONDEN:
            with open(cache_pad, "rb") as f:
                return f.read()

        if not self._robots_toestaan(url):
            print(f"[{self.bron}] robots.txt staat {url} niet toe. Overslaan.")
            return None

        wacht = self.delay - (time.time() - self._laatste_request)
        if wacht > 0:
            time.sleep(wacht)

        try:
            resp = requests.get(url, headers=self.headers, timeout=30)
        except Exception as fout:  # noqa: BLE001
            print(f"[{self.bron}] Request mislukt: {fout}. Stoppen met deze bron.")
            raise Geblokkeerd(str(fout))
        finally:
            self._laatste_request = time.time()

        if resp.status_code in (403, 429):
            if resp.headers.get("cf-mitigated") == "challenge":
                raise Geblokkeerd(f"Cloudflare challenge (HTTP {resp.status_code})")
            raise Geblokkeerd(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            print(f"[{self.bron}] HTTP {resp.status_code} voor {url}. Overslaan.")
            return None

        inhoud = resp.content
        if inhoud[:2] == b"\x1f\x8b":  # gzip-magic
            try:
                inhoud = _gzip.decompress(inhoud)
            except Exception:  # noqa: BLE001
                pass

        os.makedirs(os.path.dirname(cache_pad), exist_ok=True)
        with open(cache_pad, "wb") as f:
            f.write(inhoud)
        return inhoud

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
            resp = requests.get(url, headers=self.headers, timeout=30)
        except Exception as fout:  # noqa: BLE001
            print(f"[{self.bron}] Request mislukt: {fout}. Stoppen met deze bron.")
            raise Geblokkeerd(str(fout))
        finally:
            self._laatste_request = time.time()

        if resp.status_code in (403, 429):
            if resp.headers.get("cf-mitigated") == "challenge":
                raise Geblokkeerd(f"Cloudflare challenge (HTTP {resp.status_code})")
            raise Geblokkeerd(f"HTTP {resp.status_code}")
        if resp.status_code >= 400:
            print(f"[{self.bron}] HTTP {resp.status_code} voor {url}. Overslaan.")
            return None
        if self.detect_block_html and _blokkade_in_html(resp.text):
            raise Geblokkeerd("CAPTCHA/login-wall gedetecteerd")

        _schrijf_cache(cache_pad, resp.text)
        return resp.text


def extraheer_vacatures(html, detail_bevat, basis_url, bron, detail_regex=None):
    """Best-effort extractie van vacatures uit een zoekresultaatpagina.

    Zoekt links naar detailpagina's (href bevat 'detail_bevat', en voldoet
    optioneel aan 'detail_regex' om navigatielinks uit te sluiten). Niet elke
    site heeft titel/bedrijf/locatie in de lijst; ontbrekende velden worden
    'Onbekend'/'Nederland'. Selectors zijn generiek; pas aan als een site wijzigt.
    """
    import re
    from urllib.parse import urljoin

    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print(f"[{bron}] beautifulsoup4 niet geinstalleerd. Bron wordt overgeslagen.")
        return []

    patroon = re.compile(detail_regex) if detail_regex else None
    soup = BeautifulSoup(html, "html.parser")
    gezien, resultaat = set(), []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if detail_bevat not in href:
            continue
        if patroon and not patroon.search(href):
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


def lijst_config(config, enkelvoud, meervoud, standaard=""):
    """Geef een schone lijst terug voor config met enkelvoudige of meervoudige waarde."""
    waarde = config.get(meervoud)
    if waarde is None:
        waarde = config.get(enkelvoud, standaard)
    if isinstance(waarde, list):
        items = waarde
    else:
        items = [waarde]
    return [str(i).strip() for i in items if str(i).strip()]


def unieke_vacatures(vacatures):
    """Dedupliceer vacatures op URL en behoud de eerste variant."""
    gezien, resultaat = set(), []
    for vacature in vacatures:
        url = vacature.get("url")
        sleutel = url or (
            vacature.get("titel", "").lower(),
            vacature.get("bedrijf", "").lower(),
            vacature.get("locatie", "").lower(),
        )
        if sleutel in gezien:
            continue
        gezien.add(sleutel)
        resultaat.append(vacature)
    return resultaat


def bouw_zoek_urls(base_url, config, query_param, location_param=None,
                  page_param="page", page_start=1, page_step=1, extra_params=None):
    """Bouw zoek-URL's voor alle query/location/page-combinaties."""
    queries = lijst_config(config, "query", "queries", "")
    if location_param:
        locaties = lijst_config(config, "location", "locations", config.get("locatie", ""))
    else:
        locaties = [""]
    if not queries:
        queries = [""]
    if not locaties:
        locaties = [""]
    max_pages = int(config.get("max_pages", 2))
    urls = []
    for query in queries:
        for locatie in locaties:
            for idx in range(max_pages):
                params = dict(extra_params or {})
                if query and query_param:
                    params[query_param] = query
                if locatie and location_param:
                    params[location_param] = locatie
                if page_param:
                    params[page_param] = page_start + (idx * page_step)
                urls.append(base_url + "?" + urlencode(params))
    return urls


def _eerste_tekst(*waarden):
    for waarde in waarden:
        if isinstance(waarde, str) and waarde.strip():
            return " ".join(waarde.strip().split())
    return ""


def _jsonld_items(data):
    if isinstance(data, list):
        for item in data:
            yield from _jsonld_items(item)
    elif isinstance(data, dict):
        if "@graph" in data:
            yield from _jsonld_items(data["@graph"])
        yield data


def extraheer_detail_velden(html):
    """Haal best-effort vacaturevelden uit JSON-LD, OpenGraph en meta-tags."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    soup = BeautifulSoup(html, "html.parser")
    velden = {}

    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
        except Exception:  # noqa: BLE001
            continue
        for obj in _jsonld_items(data):
            if not isinstance(obj, dict):
                continue
            if "JobPosting" not in str(obj.get("@type", "")):
                continue
            velden["titel"] = _eerste_tekst(obj.get("title"), velden.get("titel", ""))
            org = obj.get("hiringOrganization") or {}
            if isinstance(org, dict):
                velden["bedrijf"] = _eerste_tekst(org.get("name"), velden.get("bedrijf", ""))
            loc = obj.get("jobLocation") or {}
            if isinstance(loc, list):
                loc = loc[0] if loc else {}
            adres = loc.get("address") if isinstance(loc, dict) else {}
            if isinstance(adres, dict):
                velden["locatie"] = _eerste_tekst(
                    adres.get("addressLocality"),
                    adres.get("addressRegion"),
                    velden.get("locatie", ""),
                )
            beschrijving = obj.get("description")
            if beschrijving:
                import re as _re
                schoon = _re.sub(r"<[^>]+>", " ", beschrijving).replace("&nbsp;", " ")
                velden["omschrijving"] = _eerste_tekst(schoon, velden.get("omschrijving", ""))
            velden["datum"] = _eerste_tekst(obj.get("datePosted"), velden.get("datum", ""))

    og_titel = soup.find("meta", property="og:title")
    if og_titel and og_titel.get("content"):
        velden.setdefault("titel", _eerste_tekst(og_titel["content"]))
    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        velden.setdefault("omschrijving", _eerste_tekst(meta_desc["content"]))

    return {k: v for k, v in velden.items() if v}


def verrijk_met_detailpagina(vacature, sessie):
    """Vul ontbrekende velden aan met data uit de vacaturedetailpagina."""
    url = vacature.get("url")
    if not url:
        return vacature
    try:
        html = sessie.get(url)
    except Geblokkeerd as blok:
        print(f"[{sessie.bron}] Detailpagina geblokkeerd ({blok}). Sla details over.")
        return vacature
    if not html:
        return vacature

    velden = extraheer_detail_velden(html)
    verrijkt = dict(vacature)
    for veld, waarde in velden.items():
        if waarde and (not verrijkt.get(veld) or verrijkt.get(veld) in ("Onbekend bedrijf", "Nederland", "")):
            verrijkt[veld] = waarde
    return verrijkt


def _parse_sitemap_locs(xml):
    """Geef (sub_sitemaps, paginas) terug uit een sitemap- of index-XML."""
    from xml.etree import ElementTree as ET
    try:
        root = ET.fromstring(xml)
    except Exception:  # noqa: BLE001
        return [], []
    sub, paginas = [], []
    for el in root.iter():
        if el.tag.lower().endswith("loc"):
            u = (el.text or "").strip()
            if u.endswith(".xml") or "/sitemap" in u.lower():
                sub.append(u)
            else:
                paginas.append(u)
    return sub, paginas


def lees_sitemap_urls(sitemap_url, bron, config, bevat="", max_urls=50):
    """Verzamel vacature-URL's uit een (geneste) sitemap.

    Verzamel vacature-URL's uit sitemaps. Het aantal opgehaalde sitemapbestanden
    wordt begrensd door 'max_sitemap_pages' of 'max_pages'.
    """
    sessie = PoliteSession(bron, config)
    budget = int(config.get("max_sitemap_pages", config.get("max_pages", 2)))
    te_doen, verzameld, gezien = [sitemap_url], [], set()

    while te_doen and budget > 0 and len(verzameld) < max_urls:
        url = te_doen.pop(0)
        if url in gezien:
            continue
        gezien.add(url)
        try:
            ruw = sessie.get_bytes(url)
        except Geblokkeerd as blok:
            print(f"[{bron}] Sitemap geblokkeerd ({blok}). Stoppen.")
            break
        budget -= 1
        if not ruw:
            continue
        xml = ruw.decode("utf-8", "ignore")
        sub, paginas = _parse_sitemap_locs(xml)
        for p in paginas:
            if (not bevat or bevat in p) and p not in verzameld:
                verzameld.append(p)
                if len(verzameld) >= max_urls:
                    break
        # Voeg sub-sitemaps toe als we nog niet genoeg hebben.
        te_doen.extend(s for s in sub if s not in gezien)
    return verzameld[:max_urls]


def titel_uit_slug(url):
    """Leid een leesbare titel af uit de laatste URL-slug (zonder id-prefix)."""
    slug = url.rstrip("/").split("/")[-1]
    deel = slug.split("-", 1)
    if len(deel) > 1 and deel[0].isdigit():
        slug = deel[1]
    return slug.replace("-", " ").strip().capitalize() or "Onbekende functie"


def haal_pagina_html(bron, page_urls, config):
    """Haal zoekpagina's op; stop netjes bij een blokkade."""
    max_fetch_pages = int(config.get("max_fetch_pages", len(page_urls)))
    sessie = PoliteSession(bron, config)
    htmls = []
    for url in page_urls[:max_fetch_pages]:
        try:
            html = sessie.get(url)
        except Geblokkeerd as blok:
            print(f"[{bron}] Geblokkeerd ({blok}). Stop met deze bron.")
            break
        if html:
            htmls.append(html)
    return htmls
